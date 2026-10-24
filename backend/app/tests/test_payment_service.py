import asyncio
import hashlib
import hmac
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.audit.models import AuditActorType, AuditLog
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.notifications.models import Notification
from app.modules.payments.errors import (
    PaymentAmountMismatchError,
    PaymentConflictError,
    PaymentForbiddenError,
    PaymentInvalidWebhookError,
    PaymentProviderError,
)
from app.modules.payments.gateway import (
    MockPaymentGateway,
    PaymentGatewayError,
    ProviderOrder,
)
from app.modules.payments.models import (
    PaymentEvent,
    PaymentOrder,
    PaymentStatus,
    PaymentStatusHistory,
)
from app.modules.payments.service import PaymentService

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)
DOSSIER_ID = UUID("1d561c46-c710-494b-9b11-402af341acbd")
ADMIN_ID = UUID("70fe624c-6706-4f3a-97fb-0d12f1a33db2")


class ReconciliationGateway(MockPaymentGateway):
    status = "PENDING"
    transaction_probe: Callable[[], bool] | None = None

    async def get_order(self, provider_order_id: str) -> ProviderOrder:
        if self.transaction_probe is not None:
            assert not self.transaction_probe()
        order = await super().get_order(provider_order_id)
        return ProviderOrder(
            provider_order_id=order.provider_order_id,
            checkout_url=order.checkout_url,
            qr_payload=order.qr_payload,
            status=self.status,
        )


class TrackingGateway(MockPaymentGateway):
    create_called = False
    transaction_probe: Callable[[], bool] | None = None

    async def create_order(
        self,
        *,
        order_code: str,
        amount_minor: int,
        currency: str,
        expires_at: datetime,
    ) -> ProviderOrder:
        self.create_called = True
        if self.transaction_probe is not None:
            assert not self.transaction_probe()
        return await super().create_order(
            order_code=order_code,
            amount_minor=amount_minor,
            currency=currency,
            expires_at=expires_at,
        )


class LostCheckoutResponseGateway(MockPaymentGateway):
    create_calls = 0

    async def create_order(
        self,
        *,
        order_code: str,
        amount_minor: int,
        currency: str,
        expires_at: datetime,
    ) -> ProviderOrder:
        self.create_calls += 1
        await super().create_order(
            order_code=order_code,
            amount_minor=amount_minor,
            currency=currency,
            expires_at=expires_at,
        )
        raise PaymentGatewayError("response lost")


class CancelRaceGateway(MockPaymentGateway):
    on_cancel: Callable[[], Awaitable[None]] | None = None

    async def cancel_order(
        self, provider_order_id: str, *, reason: str
    ) -> ProviderOrder:
        if self.on_cancel is not None:
            await self.on_cancel()
        return await super().cancel_order(provider_order_id, reason=reason)


async def _service(
    issue_queue: list[UUID] | None = None,
    gateway: MockPaymentGateway | None = None,
) -> tuple[
    PaymentService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    AuthPrincipal,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    user = User(
        id=UUID("60fe624c-6706-4f3a-97fb-0d12f1a33db2"),
        email="owner@cnsgroup.vn",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
    admin = User(
        id=ADMIN_ID,
        email="admin@cnsgroup.vn",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
    admin_role = Role(id=uuid4(), code="SUPER_ADMIN")
    category = Category(id=uuid4(), code="PAYABLE", name="Payable")
    dossier = Dossier(
        id=DOSSIER_ID,
        code="DOS-PAYABLE",
        owner_user_id=user.id,
        category_id=category.id,
        title="Approved dossier",
    )
    dossier._set_status_from_workflow(DossierStatus.APPROVED)
    async with sessions() as session:
        session.add_all(
            [
                user,
                admin,
                admin_role,
                UserRole(user_id=admin.id, role_id=admin_role.id),
                category,
                dossier,
            ]
        )
        await session.commit()
    ids = iter(
        (
            UUID("1734834e-5f18-4d96-bf24-c096a9ad24e7"),
            UUID("2734834e-5f18-4d96-bf24-c096a9ad24e7"),
            UUID("3734834e-5f18-4d96-bf24-c096a9ad24e7"),
            UUID("4734834e-5f18-4d96-bf24-c096a9ad24e7"),
        )
    )
    gateway = gateway or MockPaymentGateway(
        webhook_secret="payment-secret",
        uuid_factory=lambda: "provider-order",
    )
    service = PaymentService(
        session=sessions(),
        gateway=gateway,
        provider_name="mock",
        amount_minor=1_000_000,
        currency="VND",
        order_ttl_seconds=900,
        enqueue_certificate_issue=(
            issue_queue.append if issue_queue is not None else None
        ),
        clock=lambda: NOW,
        uuid_factory=lambda: next(ids),
    )
    return (
        service,
        sessions,
        engine,
        AuthPrincipal(
            user_id=user.id,
            session_id=uuid4(),
            email=user.email,
            roles=("USER",),
        ),
    )


def _webhook(
    *,
    amount_minor: int = 1_000_000,
    event_id: str = "evt-paid-1",
    event_type: str = "payment.paid",
    order_code: str | None = None,
) -> tuple[bytes, str, int]:
    timestamp = int(NOW.timestamp())
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "provider_order_id": "mock-provider-order",
        "amount_minor": amount_minor,
        "currency": "VND",
    }
    if order_code is not None:
        payload["order_code"] = order_code
    body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(
        b"payment-secret",
        str(timestamp).encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return body, signature, timestamp


def test_admin_issues_exact_payment_amount_and_notifies_owner() -> None:
    async def exercise() -> None:
        gateway = TrackingGateway(
            webhook_secret="payment-secret",
            uuid_factory=lambda: "provider-order",
        )
        service, sessions, engine, applicant = await _service(gateway=gateway)
        operator = AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="finance@cnsgroup.vn",
            roles=("VIEWER",),
            permissions=("payments.issue",),
        )

        order = await service.issue_order(
            operator,
            DOSSIER_ID,
            idempotency_key="admin-issued-payment-1",
            amount_minor=1_500_000,
            currency="VND",
            description="Phí xác lập và phát hành chứng thư",
            due_at=NOW.replace(day=7, month=8),
        )

        assert order.amount_minor == 1_500_000
        assert order.description == "Phí xác lập và phát hành chứng thư"
        assert order.issued_by_user_id == operator.user_id
        assert order.status is PaymentStatus.PENDING
        assert order.provider_order_id is None
        assert order.qr_payload is None
        assert gateway.create_called is False
        replay = await service.issue_order(
            operator,
            DOSSIER_ID,
            idempotency_key="admin-issued-payment-1",
            amount_minor=1_500_000,
            currency="VND",
            description="Phí xác lập và phát hành chứng thư",
            due_at=NOW.replace(day=7, month=8),
        )
        assert replay.id == order.id
        assert gateway.create_called is False
        with pytest.raises(PaymentConflictError):
            await service.issue_order(
                operator,
                DOSSIER_ID,
                idempotency_key="admin-issued-payment-1",
                amount_minor=1_600_000,
                currency="VND",
                description="Phí xác lập và phát hành chứng thư",
                due_at=NOW.replace(day=7, month=8),
            )
        async with sessions() as session:
            notification = await session.scalar(select(Notification))
            assert notification is not None
            assert notification.user_id == applicant.user_id
            assert notification.type == "PAYMENT_REQUEST_ISSUED"
            assert notification.data_json["actionPath"] == f"/payments/{order.id}"
            dossier = await session.get(Dossier, DOSSIER_ID)
            assert dossier is not None
            assert dossier.status is DossierStatus.PAYMENT_PENDING
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_applicant_cannot_issue_own_payment_amount() -> None:
    async def exercise() -> None:
        service, _, engine, applicant = await _service()
        with pytest.raises(PaymentForbiddenError):
            await service.issue_order(
                applicant,
                DOSSIER_ID,
                idempotency_key="applicant-must-not-issue",
                amount_minor=1_500_000,
                currency="VND",
                description="Phí xác lập và phát hành chứng thư",
                due_at=NOW.replace(day=7, month=8),
            )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_admin_can_waive_payment_and_make_dossier_ready_for_signing() -> None:
    async def exercise() -> None:
        issue_queue: list[UUID] = []
        service, sessions, engine, _ = await _service(issue_queue=issue_queue)
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=uuid4(),
            email="admin@cnsgroup.vn",
            roles=("SUPER_ADMIN",),
            permissions=("payments.issue",),
        )

        candidates = await service.list_payment_candidates(admin)
        assert [(item.dossier_id, item.dossier_code) for item in candidates] == [
            (DOSSIER_ID, "DOS-PAYABLE")
        ]

        waived = await service.waive_payment(
            admin,
            DOSSIER_ID,
            idempotency_key="waive-payment-1",
            reason="Hồ sơ thuộc chương trình hỗ trợ miễn phí.",
        )

        assert waived.dossier_id == DOSSIER_ID
        assert waived.status is DossierStatus.PAID
        assert issue_queue == [DOSSIER_ID]
        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            assert dossier is not None
            assert dossier.status is DossierStatus.PAID
            notifications = tuple((await session.scalars(select(Notification))).all())
            assert {item.type for item in notifications} == {
                "PAYMENT_WAIVED",
                "DOSSIER_READY_FOR_BLOCKCHAIN",
            }
            notification_actions = {
                item.type: item.data_json["actionPath"] for item in notifications
            }
            assert notification_actions == {
                "PAYMENT_WAIVED": f"/dossiers/{DOSSIER_ID}",
                "DOSSIER_READY_FOR_BLOCKCHAIN": "/blockchain",
            }

        replay = await service.waive_payment(
            admin,
            DOSSIER_ID,
            idempotency_key="waive-payment-1",
            reason="Hồ sơ thuộc chương trình hỗ trợ miễn phí.",
        )
        assert replay.status is DossierStatus.PAID
        assert issue_queue == [DOSSIER_ID]

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_create_order_is_idempotent_and_transitions_dossier() -> None:
    async def exercise() -> None:
        gateway = TrackingGateway(webhook_secret="payment-secret")
        service, sessions, engine, principal = await _service(gateway=gateway)
        gateway.transaction_probe = lambda: service._session.in_transaction()
        created = await service.create_order(
            principal,
            DOSSIER_ID,
            idempotency_key="create-payment-1",
        )
        replay = await service.create_order(
            principal,
            DOSSIER_ID,
            idempotency_key="create-payment-1",
        )

        assert replay.id == created.id
        assert created.amount_minor == 1_000_000
        assert created.checkout_url is not None
        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            count = await session.scalar(select(func.count()).select_from(PaymentOrder))
            assert dossier is not None
            assert dossier.status is DossierStatus.PAYMENT_PENDING
            assert count == 1
            audits = tuple((await session.scalars(select(AuditLog))).all())
            assert [row.action for row in audits] == ["payment.order.created"]
            assert audits[0].actor_user_id == principal.user_id
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_payment_history_records_initiator_and_allows_read_permission() -> None:
    async def exercise() -> None:
        service, sessions, engine, applicant = await _service()
        order = await service.create_order(
            applicant,
            DOSSIER_ID,
            idempotency_key="history-payment-1",
        )
        reader = AuthPrincipal(
            user_id=applicant.user_id,
            session_id=uuid4(),
            email=applicant.email,
            roles=("USER",),
            permissions=("payments.read", "payments.export"),
        )

        async with sessions() as session:
            persisted = await session.get(PaymentOrder, order.id)
            history = tuple(
                (
                    await session.scalars(
                        select(PaymentStatusHistory).where(
                            PaymentStatusHistory.payment_order_id == order.id
                        )
                    )
                ).all()
            )
            assert persisted is not None
            assert persisted.initiated_by_user_id == applicant.user_id
        assert {(item.from_status, item.to_status) for item in history} == {
            (None, "PROCESSING"),
            ("PROCESSING", "PENDING"),
        }

        page, total = await service.list_admin_history(
            reader,
            status=None,
            created_from=None,
            created_to=None,
            query="owner@cnsgroup.vn",
            page=1,
            page_size=10,
        )
        assert total == 1
        assert page.rows[0].applicant_email == "owner@cnsgroup.vn"
        assert page.rows[0].initiated_by_email == "owner@cnsgroup.vn"
        assert page.summary.status_counts == {"PENDING": 1}
        detail = await service.get_admin_history_detail(reader, order.id)
        assert [
            (item.from_status, item.to_status) for item in detail.status_history
        ] == [(None, "PROCESSING"), ("PROCESSING", "PENDING")]
        exported = await service.export_admin_history(
            reader,
            status=None,
            created_from=None,
            created_to=None,
            query=None,
        )
        assert len(exported) == 1
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_lost_checkout_response_keeps_reservation_and_recovers_without_new_link() -> (
    None
):
    async def exercise() -> None:
        gateway = LostCheckoutResponseGateway(
            webhook_secret="payment-secret", uuid_factory=lambda: "provider-order"
        )
        service, sessions, engine, principal = await _service(gateway=gateway)
        with pytest.raises(PaymentProviderError):
            await service.create_order(
                principal, DOSSIER_ID, idempotency_key="lost-response"
            )
        async with sessions() as session:
            reserved = await session.scalar(select(PaymentOrder))
            assert reserved is not None
            assert reserved.status is PaymentStatus.PROCESSING
            assert reserved.provider_order_id is None
            order_id = reserved.id
        recovered = await service.create_order(
            principal, DOSSIER_ID, idempotency_key="lost-response"
        )
        assert recovered.id == order_id
        assert recovered.status is PaymentStatus.PENDING
        assert recovered.checkout_url is not None
        assert gateway.create_calls == 1
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_paid_webhook_can_settle_a_reserved_order_before_checkout_response() -> None:
    async def exercise() -> None:
        issue_queue: list[UUID] = []
        gateway = LostCheckoutResponseGateway(
            webhook_secret="payment-secret", uuid_factory=lambda: "provider-order"
        )
        service, sessions, engine, principal = await _service(issue_queue, gateway)
        with pytest.raises(PaymentProviderError):
            await service.create_order(
                principal, DOSSIER_ID, idempotency_key="webhook-before-response"
            )
        async with sessions() as session:
            reserved = await session.scalar(select(PaymentOrder))
            assert reserved is not None
            order_code = reserved.order_code
        body, signature, timestamp = _webhook(order_code=order_code)
        paid = await service.process_webhook(
            raw_body=body, signature=signature, timestamp=timestamp
        )
        assert paid.status is PaymentStatus.PAID
        assert paid.provider_order_id == "mock-provider-order"
        assert issue_queue == [DOSSIER_ID]
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_reconciliation_worker_recovers_a_reserved_checkout() -> None:
    async def exercise() -> None:
        gateway = LostCheckoutResponseGateway(
            webhook_secret="payment-secret", uuid_factory=lambda: "provider-order"
        )
        service, sessions, engine, principal = await _service(gateway=gateway)
        with pytest.raises(PaymentProviderError):
            await service.create_order(
                principal, DOSSIER_ID, idempotency_key="worker-recovers-checkout"
            )
        assert await service.reconcile_pending() == 1
        async with sessions() as session:
            order = await session.scalar(select(PaymentOrder))
            assert order is not None
            assert order.status is PaymentStatus.PENDING
            assert order.provider_order_id == "mock-provider-order"
            assert order.metadata_json["checkout_url"] is not None
        assert gateway.create_calls == 1
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_applicant_cancels_pending_order_and_can_restart_payment() -> None:
    async def exercise() -> None:
        service, sessions, engine, principal = await _service()
        order = await service.create_order(
            principal,
            DOSSIER_ID,
            idempotency_key="create-payment-cancel",
        )

        cancelled = await service.cancel_order(
            principal,
            order.id,
            reason="Tôi muốn kiểm tra lại thông tin hồ sơ",
        )
        replay = await service.cancel_order(
            principal,
            order.id,
            reason="Yêu cầu được gửi lại do mất kết nối",
        )

        assert cancelled.status is PaymentStatus.CANCELLED
        assert replay.status is PaymentStatus.CANCELLED
        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            assert dossier is not None
            assert dossier.status is DossierStatus.APPROVED
            audits = tuple((await session.scalars(select(AuditLog))).all())
            assert [row.action for row in audits] == [
                "payment.order.created",
                "payment.order.cancelled",
            ]
            assert audits[-1].actor_user_id == principal.user_id

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_webhook_paid_during_cancellation_keeps_payment_paid() -> None:
    async def exercise() -> None:
        gateway = CancelRaceGateway(
            webhook_secret="payment-secret", uuid_factory=lambda: "provider-order"
        )
        service, sessions, engine, principal = await _service(gateway=gateway)
        order = await service.create_order(
            principal, DOSSIER_ID, idempotency_key="cancel-race"
        )
        body, signature, timestamp = _webhook()

        async def settle() -> None:
            await service.process_webhook(
                raw_body=body, signature=signature, timestamp=timestamp
            )

        gateway.on_cancel = settle
        result = await service.cancel_order(
            principal, order.id, reason="Applicant cancelled checkout"
        )
        assert result.status is PaymentStatus.PAID
        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            assert dossier is not None
            assert dossier.status is DossierStatus.PAID
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_payment_order_and_dossier_transition_roll_back_when_audit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        gateway = TrackingGateway(
            webhook_secret="payment-secret",
            uuid_factory=lambda: "provider-order",
        )
        service, sessions, engine, principal = await _service(gateway=gateway)

        def fail_audit(**_: object) -> None:
            raise RuntimeError("audit storage unavailable")

        monkeypatch.setattr(service._audit_service, "record", fail_audit)
        with pytest.raises(RuntimeError, match="audit storage unavailable"):
            await service.create_order(
                principal,
                DOSSIER_ID,
                idempotency_key="create-payment-rollback",
            )

        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            assert dossier is not None
            assert dossier.status is DossierStatus.APPROVED
            assert (await session.scalar(select(PaymentOrder))) is None
            assert (await session.scalar(select(AuditLog))) is None
        assert gateway.create_called is False

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_paid_webhook_is_atomic_and_duplicate_is_idempotent() -> None:
    async def exercise() -> None:
        issue_queue: list[UUID] = []
        service, sessions, engine, principal = await _service(issue_queue)
        order = await service.create_order(
            principal,
            DOSSIER_ID,
            idempotency_key="create-payment-2",
        )
        body, signature, timestamp = _webhook()

        paid = await service.process_webhook(
            raw_body=body,
            signature=signature,
            timestamp=timestamp,
        )
        duplicate = await service.process_webhook(
            raw_body=body,
            signature=signature,
            timestamp=timestamp,
        )

        assert paid.id == duplicate.id == order.id
        assert paid.status is PaymentStatus.PAID
        assert issue_queue == [DOSSIER_ID]
        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            event_count = await session.scalar(
                select(func.count()).select_from(PaymentEvent)
            )
            assert dossier is not None
            assert dossier.status is DossierStatus.PAID
            assert event_count == 1
            audits = tuple((await session.scalars(select(AuditLog))).all())
            assert [row.action for row in audits] == [
                "payment.order.created",
                "payment.webhook.processed",
            ]
            assert audits[-1].actor_type is AuditActorType.SERVICE
            assert audits[-1].actor_service == "payment-webhook"
            assert "signature" not in str(audits[-1].after_json).lower()
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_stale_failed_webhook_cannot_regress_paid_order() -> None:
    async def exercise() -> None:
        issue_queue: list[UUID] = []
        service, sessions, engine, principal = await _service(issue_queue)
        order = await service.create_order(
            principal, DOSSIER_ID, idempotency_key="stale-failed-webhook"
        )
        body, signature, timestamp = _webhook()
        await service.process_webhook(
            raw_body=body, signature=signature, timestamp=timestamp
        )
        failed_body, failed_signature, timestamp = _webhook(
            event_id="evt-failed-late", event_type="payment.failed"
        )
        result = await service.process_webhook(
            raw_body=failed_body,
            signature=failed_signature,
            timestamp=timestamp,
        )
        assert result.id == order.id
        assert result.status is PaymentStatus.PAID
        assert issue_queue == [DOSSIER_ID]
        async with sessions() as session:
            events = tuple((await session.scalars(select(PaymentEvent))).all())
            assert len(events) == 2
            assert all(event.processed_at is not None for event in events)
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_late_paid_webhook_after_cancellation_is_recorded_for_review() -> None:
    async def exercise() -> None:
        issue_queue: list[UUID] = []
        service, sessions, engine, principal = await _service(issue_queue)
        order = await service.create_order(
            principal, DOSSIER_ID, idempotency_key="late-paid-after-cancel"
        )
        await service.cancel_order(principal, order.id, reason="Changed payment method")
        body, signature, timestamp = _webhook(event_id="evt-paid-after-cancel")

        result = await service.process_webhook(
            raw_body=body, signature=signature, timestamp=timestamp
        )
        assert result.status is PaymentStatus.CANCELLED
        assert issue_queue == []
        async with sessions() as session:
            event = await session.scalar(
                select(PaymentEvent).where(
                    PaymentEvent.provider_event_id == "evt-paid-after-cancel"
                )
            )
            dossier = await session.get(Dossier, DOSSIER_ID)
            audits = tuple((await session.scalars(select(AuditLog))).all())
            assert event is not None and event.processed_at is not None
            assert dossier is not None and dossier.status is DossierStatus.APPROVED
            assert audits[-1].action == "payment.webhook.conflict"
            assert audits[-1].after_json == {"outcome": "PAID_AFTER_CANCELLED"}
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_stale_processing_webhook_does_not_reopen_cancelled_order() -> None:
    async def exercise() -> None:
        service, sessions, engine, principal = await _service()
        order = await service.create_order(
            principal, DOSSIER_ID, idempotency_key="stale-processing-after-cancel"
        )
        await service.cancel_order(principal, order.id, reason="Changed payment method")
        body, signature, timestamp = _webhook(
            event_id="evt-processing-after-cancel", event_type="payment.processing"
        )
        result = await service.process_webhook(
            raw_body=body, signature=signature, timestamp=timestamp
        )
        assert result.status is PaymentStatus.CANCELLED
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_stale_provider_snapshot_does_not_reopen_cancelled_order() -> None:
    async def exercise() -> None:
        gateway = ReconciliationGateway(webhook_secret="payment-secret")
        service, sessions, engine, principal = await _service(gateway=gateway)
        order = await service.create_order(
            principal, DOSSIER_ID, idempotency_key="stale-provider-after-cancel"
        )
        await service.cancel_order(principal, order.id, reason="Changed payment method")
        finance = AuthPrincipal(
            user_id=principal.user_id,
            session_id=principal.session_id,
            email=principal.email,
            roles=("SUPER_ADMIN",),
        )
        gateway.status = "PENDING"
        result = await service.reconcile_order(finance, order.id)
        assert result.status is PaymentStatus.CANCELLED
        gateway.status = "PAID"
        conflicted = await service.reconcile_order(finance, order.id)
        assert conflicted.status is PaymentStatus.CANCELLED
        async with sessions() as session:
            audits = tuple((await session.scalars(select(AuditLog))).all())
            assert audits[-1].action == "payment.reconciliation.conflict"
            assert audits[-1].after_json == {"outcome": "PAID_AFTER_CANCELLED"}
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_webhook_rejects_tampering_and_wrong_amount_without_marking_paid() -> None:
    async def exercise() -> None:
        service, sessions, engine, principal = await _service()
        await service.create_order(
            principal,
            DOSSIER_ID,
            idempotency_key="create-payment-3",
        )
        body, signature, timestamp = _webhook(amount_minor=999)

        with pytest.raises(PaymentInvalidWebhookError):
            await service.process_webhook(
                raw_body=body + b" ",
                signature=signature,
                timestamp=timestamp,
            )
        with pytest.raises(PaymentAmountMismatchError):
            await service.process_webhook(
                raw_body=body,
                signature=signature,
                timestamp=timestamp,
            )

        async with sessions() as session:
            order = await session.scalar(select(PaymentOrder))
            dossier = await session.get(Dossier, DOSSIER_ID)
            assert order is not None
            assert order.status is PaymentStatus.PENDING
            assert dossier is not None
            assert dossier.status is DossierStatus.PAYMENT_PENDING
            audits = tuple((await session.scalars(select(AuditLog))).all())
            assert [row.action for row in audits] == [
                "payment.order.created",
                "payment.webhook.rejected",
            ]
            assert audits[-1].after_json == {"outcome": "AMOUNT_MISMATCH"}
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_reconciliation_confirms_paid_once_and_enqueues_issuance_once() -> None:
    async def exercise() -> None:
        issue_queue: list[UUID] = []
        gateway = ReconciliationGateway(
            webhook_secret="payment-secret",
            uuid_factory=lambda: "provider-order",
        )
        service, sessions, engine, applicant = await _service(issue_queue, gateway)
        gateway.transaction_probe = lambda: service._session.in_transaction()
        order = await service.create_order(
            applicant,
            DOSSIER_ID,
            idempotency_key="create-payment-reconcile-paid",
        )
        finance = AuthPrincipal(
            user_id=applicant.user_id,
            session_id=applicant.session_id,
            email=applicant.email,
            roles=("SUPER_ADMIN",),
        )
        gateway.status = "PAID"

        paid = await service.reconcile_order(finance, order.id)
        replay = await service.reconcile_order(finance, order.id)

        assert paid.status is PaymentStatus.PAID
        assert replay.status is PaymentStatus.PAID
        assert issue_queue == [DOSSIER_ID]
        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            assert dossier is not None
            assert dossier.status is DossierStatus.PAID
            audits = tuple((await session.scalars(select(AuditLog))).all())
            assert [row.action for row in audits] == [
                "payment.order.created",
                "payment.order.reconciled",
            ]
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_stale_provider_status_cannot_regress_a_paid_order() -> None:
    async def exercise() -> None:
        issue_queue: list[UUID] = []
        gateway = ReconciliationGateway(
            webhook_secret="payment-secret",
            uuid_factory=lambda: "provider-order",
        )
        service, sessions, engine, applicant = await _service(issue_queue, gateway)
        order = await service.create_order(
            applicant, DOSSIER_ID, idempotency_key="stale-paid-order"
        )
        body, signature, timestamp = _webhook()
        await service.process_webhook(
            raw_body=body, signature=signature, timestamp=timestamp
        )
        finance = AuthPrincipal(
            user_id=applicant.user_id,
            session_id=applicant.session_id,
            email=applicant.email,
            roles=("SUPER_ADMIN",),
        )
        for stale_status in ("PROCESSING", "FAILED", "CANCELLED"):
            gateway.status = stale_status
            reconciled = await service.reconcile_order(finance, order.id)
            assert reconciled.status is PaymentStatus.PAID
        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            assert dossier is not None
            assert dossier.status is DossierStatus.PAID
        assert issue_queue == [DOSSIER_ID]
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_reconciliation_accepts_granular_permission_without_privileged_role() -> None:
    async def exercise() -> None:
        gateway = ReconciliationGateway(
            webhook_secret="payment-secret",
            uuid_factory=lambda: "provider-order",
        )
        service, _, engine, applicant = await _service(gateway=gateway)
        order = await service.create_order(
            applicant,
            DOSSIER_ID,
            idempotency_key="create-payment-reconcile-permission",
        )
        operator = AuthPrincipal(
            user_id=applicant.user_id,
            session_id=applicant.session_id,
            email=applicant.email,
            roles=("VIEWER",),
            permissions=("payments.reconcile",),
        )

        reconciled = await service.reconcile_order(operator, order.id)

        assert reconciled.id == order.id
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_admin_payment_list_includes_status_and_dossier_context() -> None:
    async def exercise() -> None:
        service, _, engine, applicant = await _service()
        order = await service.create_order(
            applicant,
            DOSSIER_ID,
            idempotency_key="create-payment-admin-list",
        )
        finance = AuthPrincipal(
            user_id=applicant.user_id,
            session_id=applicant.session_id,
            email=applicant.email,
            roles=("SUPER_ADMIN",),
        )

        rows = await service.list_admin_orders(finance, status=None, limit=50)

        assert len(rows) == 1
        assert rows[0].order.id == order.id
        assert rows[0].order.status is PaymentStatus.PENDING
        assert rows[0].dossier_code == "DOS-PAYABLE"
        assert rows[0].dossier_title == "Approved dossier"
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_admin_payment_list_requires_reconciliation_permission() -> None:
    async def exercise() -> None:
        service, _, engine, applicant = await _service()

        with pytest.raises(PaymentForbiddenError):
            await service.list_admin_orders(applicant, status=None, limit=50)

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_reconciliation_records_cancelled_provider_state() -> None:
    async def exercise() -> None:
        gateway = ReconciliationGateway(
            webhook_secret="payment-secret",
            uuid_factory=lambda: "provider-order",
        )
        service, sessions, engine, applicant = await _service(gateway=gateway)
        order = await service.create_order(
            applicant,
            DOSSIER_ID,
            idempotency_key="create-payment-reconcile-cancelled",
        )
        finance = AuthPrincipal(
            user_id=applicant.user_id,
            session_id=applicant.session_id,
            email=applicant.email,
            roles=("SUPER_ADMIN",),
        )
        gateway.status = "CANCELLED"

        cancelled = await service.reconcile_order(finance, order.id)

        assert cancelled.status is PaymentStatus.CANCELLED
        async with sessions() as session:
            audits = tuple((await session.scalars(select(AuditLog))).all())
            assert [row.action for row in audits] == [
                "payment.order.created",
                "payment.order.reconciled",
            ]
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_manual_confirmation_is_audited_without_evidence_or_note() -> None:
    async def exercise() -> None:
        service, sessions, engine, applicant = await _service()
        order = await service.create_order(
            applicant,
            DOSSIER_ID,
            idempotency_key="create-payment-manual",
        )
        finance = AuthPrincipal(
            user_id=applicant.user_id,
            session_id=applicant.session_id,
            email=applicant.email,
            roles=("SUPER_ADMIN",),
        )

        confirmed = await service.confirm_manual(
            finance,
            order.id,
            evidence_reference="bank-reference-123",
            note="Confirmed against the finance statement.",
        )
        assert confirmed.status is PaymentStatus.PAID

        async with sessions() as session:
            audits = tuple((await session.scalars(select(AuditLog))).all())
            manual = audits[-1]
            assert manual.action == "payment.order.manually_confirmed"
            assert manual.after_json == {"status": "PAID"}
            assert "bank-reference" not in str(manual.after_json)
            assert "finance statement" not in str(manual.after_json)

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
