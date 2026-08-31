import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.billing.errors import PriceCatalogConflictError
from app.modules.billing.models import (
    FeeObligation,
    FeeObligationStatus,
    PriceCatalogEntry,
    PriceCatalogStatus,
    PriceCatalogVersion,
)
from app.modules.billing.service import BillingService
from app.modules.dossiers.models import Category, Dossier, DossierStatus, DossierType
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.notifications.models import Notification

NOW = datetime(2026, 8, 30, 9, 0, tzinfo=UTC)
ACTOR_ID = UUID("10000000-0000-4000-8000-000000000001")


def test_approved_dossier_creates_one_locked_fee_obligation() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        owner = User(
            id=uuid4(),
            email="billing-owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        actor = User(
            id=ACTOR_ID,
            email="approver@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="BILL-DUE", name="Billing due")
        dossier_type = DossierType(
            id=uuid4(),
            category_id=category.id,
            code="TRADEMARK",
            name="Trademark",
        )
        dossier = Dossier(
            id=uuid4(),
            code="DOS-BILL-DUE",
            owner_user_id=owner.id,
            category_id=category.id,
            dossier_type_id=dossier_type.id,
            title="Approved trademark",
        )
        dossier._set_status_from_workflow(DossierStatus.APPROVED)
        catalog = PriceCatalogVersion(
            id=uuid4(),
            version_no=1,
            status=PriceCatalogStatus.PUBLISHED,
            effective_from=NOW - timedelta(days=1),
            published_at=NOW - timedelta(days=1),
        )
        price = PriceCatalogEntry(
            id=uuid4(),
            catalog_version_id=catalog.id,
            dossier_type_id=dossier_type.id,
            service_code="STANDARD",
            display_name="Phí xác lập và phát hành chứng thư",
            amount_minor=1_000_000,
            currency="VND",
            tax_mode="UNSPECIFIED",
        )
        async with sessions() as session:
            session.add_all(
                [owner, actor, category, dossier_type, dossier, catalog, price]
            )
            await session.commit()

        service = BillingService(
            session=sessions(),
            payment_term_days=7,
            clock=lambda: NOW,
            uuid_factory=lambda: UUID("20000000-0000-4000-8000-000000000001"),
        )
        first = await service.create_for_approved_dossier(
            dossier_id=dossier.id,
            actor_user_id=ACTOR_ID,
        )
        second = await service.create_for_approved_dossier(
            dossier_id=dossier.id,
            actor_user_id=ACTOR_ID,
        )

        assert first.id == second.id
        assert first.status is FeeObligationStatus.OPEN
        assert first.amount_minor == 1_000_000
        assert first.price_catalog_version_id == catalog.id
        assert first.due_at == NOW + timedelta(days=7)
        async with sessions() as session:
            stored = await session.get(FeeObligation, first.id)
            stored_dossier = await session.get(Dossier, dossier.id)
            notification = await session.scalar(
                select(Notification).where(Notification.user_id == owner.id)
            )
            count = await session.scalar(select(func.count(FeeObligation.id)))
        assert stored is not None
        assert stored.price_snapshot_json["amountMinor"] == 1_000_000
        assert stored_dossier is not None
        assert stored_dossier.status is DossierStatus.PAYMENT_PENDING
        assert notification is not None
        assert notification.type == "FEE_OBLIGATION_CREATED"
        assert notification.data_json["feeObligationId"] == str(first.id)
        assert count == 1
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_missing_price_does_not_move_the_approved_dossier() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        owner = User(
            id=uuid4(),
            email="no-price@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        actor = User(
            id=ACTOR_ID,
            email="approver@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="NO-PRICE", name="No price")
        dossier_type = DossierType(
            id=uuid4(),
            category_id=category.id,
            code="OTHER",
            name="Other",
        )
        dossier = Dossier(
            id=uuid4(),
            code="DOS-NO-PRICE",
            owner_user_id=owner.id,
            category_id=category.id,
            dossier_type_id=dossier_type.id,
            title="No price dossier",
        )
        dossier._set_status_from_workflow(DossierStatus.APPROVED)
        async with sessions() as session:
            session.add_all([owner, actor, category, dossier_type, dossier])
            await session.commit()

        service = BillingService(
            session=sessions(), payment_term_days=7, clock=lambda: NOW
        )
        with pytest.raises(PriceCatalogConflictError, match="effective price"):
            await service.create_for_approved_dossier(
                dossier_id=dossier.id,
                actor_user_id=ACTOR_ID,
            )
        async with sessions() as session:
            stored_dossier = await session.get(Dossier, dossier.id)
            count = await session.scalar(select(func.count(FeeObligation.id)))
        assert stored_dossier is not None
        assert stored_dossier.status is DossierStatus.APPROVED
        assert count == 0
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
