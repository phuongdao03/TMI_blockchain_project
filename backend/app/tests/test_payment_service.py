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
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.payments.errors import (
    PaymentAmountMismatchError,
    PaymentInvalidWebhookError,
)
from app.modules.payments.gateway import MockPaymentGateway
from app.modules.payments.models import PaymentEvent, PaymentOrder, PaymentStatus
from app.modules.payments.service import PaymentService

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)
DOSSIER_ID = UUID("1d561c46-c710-494b-9b11-402af341acbd")


async def _service(
    issue_queue: list[UUID] | None = None,
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
    gateway = MockPaymentGateway(
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
            roles=("APPLICANT",),
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
            count = await session.scalar(
                select(func.count()).select_from(PaymentOrder)
            )
            assert dossier is not None
            assert dossier.status is DossierStatus.PAYMENT_PENDING
            assert count == 1
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
        assert issue_queue == [DOSSIER_ID, DOSSIER_ID]
        async with sessions() as session:
            dossier = await session.get(Dossier, DOSSIER_ID)
            event_count = await session.scalar(
                select(func.count()).select_from(PaymentEvent)
            )
            assert dossier is not None
            assert dossier.status is DossierStatus.PAID
            assert event_count == 1
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
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
