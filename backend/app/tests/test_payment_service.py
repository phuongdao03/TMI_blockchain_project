import asyncio
import hashlib
import hmac
import json
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
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.notifications.models import Notification
from app.modules.payments.errors import (
    PaymentAmountMismatchError,
    PaymentForbiddenError,
    PaymentInvalidWebhookError,
)
from app.modules.payments.gateway import MockPaymentGateway, ProviderOrder
from app.modules.payments.models import PaymentEvent, PaymentOrder, PaymentStatus
from app.modules.payments.service import PaymentService

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)
DOSSIER_ID = UUID("1d561c46-c710-494b-9b11-402af341acbd")


class ReconciliationGateway(MockPaymentGateway):
    status = "PENDING"

    async def get_order(self, provider_order_id: str) -> ProviderOrder:
        order = await super().get_order(provider_order_id)
        return ProviderOrder(
            provider_order_id=order.provider_order_id,
            checkout_url=order.checkout_url,
            qr_payload=order.qr_payload,
            status=self.status,
        )


class TrackingGateway(MockPaymentGateway):
    create_called = False

    async def create_order(
        self,
        *,
        order_code: str,
        amount_minor: int,
        currency: str,
        expires_at: datetime,
    ) -> ProviderOrder:
        self.create_called = True
        return await super().create_order(
            order_code=order_code,
            amount_minor=amount_minor,
            currency=currency,
            expires_at=expires_at,
        )


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
        email="owner@tmigroup.vn",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
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
        session.add_all([user, category, dossier])
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
) -> tuple[bytes, str, int]:
    timestamp = int(NOW.timestamp())
    body = json.dumps(
        {
            "event_id": event_id,
            "event_type": "payment.paid",
            "provider_order_id": "mock-provider-order",
            "amount_minor": amount_minor,
            "currency": "VND",
        },
        separators=(",", ":"),
    ).encode()
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
            email="finance@tmigroup.vn",
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
        async with sessions() as session:
            notification = await session.scalar(select(Notification))
            assert notification is not None
            assert notification.user_id == applicant.user_id
            assert notification.type == "PAYMENT_REQUEST_ISSUED"
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


def test_create_order_is_idempotent_and_transitions_dossier() -> None:
    async def exercise() -> None:
        service, sessions, engine, principal = await _service()
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
