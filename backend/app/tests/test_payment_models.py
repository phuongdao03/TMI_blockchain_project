import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.dossiers.models import Category, Dossier
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.payments.models import PaymentEvent, PaymentOrder, PaymentStatus


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return session_factory, engine


def test_payment_order_uses_minor_units_and_unique_idempotency() -> None:
    async def exercise() -> None:
        session_factory, engine = await _database()
        user = User(
            id=uuid4(),
            email="payment-owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="PAYMENT", name="Payment")
        dossier = Dossier(
            id=uuid4(),
            code="DOS-PAYMENT",
            owner_user_id=user.id,
            category_id=category.id,
            title="Payment dossier",
        )
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        async with session_factory() as session:
            session.add_all([user, category, dossier])
            await session.commit()
            session.add_all(
                [
                    PaymentOrder(
                        id=uuid4(),
                        order_code="PAY-000001",
                        dossier_id=dossier.id,
                        provider="mock",
                        amount_minor=1_000_000,
                        currency="VND",
                        status=PaymentStatus.PENDING,
                        expires_at=expires_at,
                        idempotency_key="same-key",
                        metadata_json={},
                    ),
                    PaymentOrder(
                        id=uuid4(),
                        order_code="PAY-000002",
                        dossier_id=dossier.id,
                        provider="mock",
                        amount_minor=1_000_000,
                        currency="VND",
                        status=PaymentStatus.PENDING,
                        expires_at=expires_at,
                        idempotency_key="same-key",
                        metadata_json={},
                    ),
                ]
            )
            with pytest.raises(IntegrityError):
                await session.commit()
        await engine.dispose()

    asyncio.run(exercise())


def test_provider_event_id_is_unique() -> None:
    async def exercise() -> None:
        session_factory, engine = await _database()
        order_id = uuid4()
        async with session_factory() as session:
            session.add_all(
                [
                    PaymentEvent(
                        id=uuid4(),
                        payment_order_id=order_id,
                        provider_event_id="evt-unique",
                        event_type="payment.paid",
                        signature_valid=True,
                        payload_redacted={},
                    ),
                    PaymentEvent(
                        id=uuid4(),
                        payment_order_id=order_id,
                        provider_event_id="evt-unique",
                        event_type="payment.paid",
                        signature_valid=True,
                        payload_redacted={},
                    ),
                ]
            )
            with pytest.raises(IntegrityError):
                await session.commit()
        await engine.dispose()

    asyncio.run(exercise())
