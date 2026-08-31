import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.billing.errors import PriceCatalogConflictError
from app.modules.billing.models import (
    PriceCatalogEntry,
    PriceCatalogStatus,
    PriceCatalogVersion,
)
from app.modules.billing.service import PriceCatalogService
from app.modules.dossiers.models import Category, DossierType
from app.modules.media.models import MediaAsset  # noqa: F401

NOW = datetime(2026, 8, 30, 8, 0, tzinfo=UTC)


def test_resolve_price_returns_the_single_effective_published_snapshot() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        category = Category(id=uuid4(), code="BILLING", name="Billing")
        dossier_type = DossierType(
            id=uuid4(),
            category_id=category.id,
            code="ARTWORK",
            name="Artwork",
        )
        version = PriceCatalogVersion(
            id=uuid4(),
            version_no=1,
            status=PriceCatalogStatus.PUBLISHED,
            effective_from=NOW - timedelta(days=1),
            effective_to=None,
            published_at=NOW - timedelta(days=1),
        )
        entry = PriceCatalogEntry(
            id=uuid4(),
            catalog_version_id=version.id,
            dossier_type_id=dossier_type.id,
            service_code="STANDARD",
            display_name="Phí xác lập và phát hành chứng thư",
            amount_minor=1_000_000,
            currency="VND",
            tax_mode="UNSPECIFIED",
        )
        async with sessions() as session:
            session.add_all([category, dossier_type, version, entry])
            await session.commit()
            resolved = await PriceCatalogService(session).resolve_price(
                dossier_type_id=dossier_type.id,
                service_code="STANDARD",
                effective_at=NOW,
            )

        assert resolved.catalog_version_id == version.id
        assert resolved.entry_id == entry.id
        assert resolved.amount_minor == 1_000_000
        assert resolved.currency == "VND"
        await engine.dispose()

    asyncio.run(exercise())


def test_resolve_price_fails_closed_when_no_published_price_exists() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with sessions() as session:
            with pytest.raises(PriceCatalogConflictError, match="effective price"):
                await PriceCatalogService(session).resolve_price(
                    dossier_type_id=uuid4(),
                    service_code="STANDARD",
                    effective_at=NOW,
                )
        await engine.dispose()

    asyncio.run(exercise())


def test_resolve_price_rejects_overlapping_published_versions() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        category = Category(id=uuid4(), code="OVERLAP", name="Overlap")
        dossier_type = DossierType(
            id=uuid4(),
            category_id=category.id,
            code="DOCUMENT",
            name="Document",
        )
        versions = [
            PriceCatalogVersion(
                id=uuid4(),
                version_no=index,
                status=PriceCatalogStatus.PUBLISHED,
                effective_from=NOW - timedelta(days=index),
                effective_to=None,
                published_at=NOW - timedelta(days=index),
            )
            for index in (1, 2)
        ]
        entries = [
            PriceCatalogEntry(
                id=uuid4(),
                catalog_version_id=version.id,
                dossier_type_id=dossier_type.id,
                service_code="STANDARD",
                display_name="Standard fee",
                amount_minor=index * 1_000_000,
                currency="VND",
                tax_mode="UNSPECIFIED",
            )
            for index, version in enumerate(versions, start=1)
        ]
        async with sessions() as session:
            session.add_all([category, dossier_type, *versions, *entries])
            await session.commit()
            with pytest.raises(PriceCatalogConflictError, match="multiple"):
                await PriceCatalogService(session).resolve_price(
                    dossier_type_id=dossier_type.id,
                    service_code="STANDARD",
                    effective_at=NOW,
                )
        await engine.dispose()

    asyncio.run(exercise())
