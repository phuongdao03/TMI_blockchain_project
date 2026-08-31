from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import (
    FeeObligation,
    PriceCatalogEntry,
    PriceCatalogStatus,
    PriceCatalogVersion,
)


class PriceCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def effective_entries(
        self,
        *,
        dossier_type_id: UUID,
        service_code: str,
        effective_at: datetime,
    ) -> tuple[tuple[PriceCatalogVersion, PriceCatalogEntry], ...]:
        rows = await self._session.execute(
            select(PriceCatalogVersion, PriceCatalogEntry)
            .join(
                PriceCatalogEntry,
                PriceCatalogEntry.catalog_version_id == PriceCatalogVersion.id,
            )
            .where(
                PriceCatalogVersion.status == PriceCatalogStatus.PUBLISHED,
                PriceCatalogVersion.effective_from <= effective_at,
                or_(
                    PriceCatalogVersion.effective_to.is_(None),
                    PriceCatalogVersion.effective_to > effective_at,
                ),
                PriceCatalogEntry.dossier_type_id == dossier_type_id,
                PriceCatalogEntry.service_code == service_code,
            )
            .limit(2)
        )
        return tuple(rows.tuples())


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_obligation(self, obligation: FeeObligation) -> None:
        self._session.add(obligation)

    async def obligation_by_id(
        self, obligation_id: UUID, *, for_update: bool = False
    ) -> FeeObligation | None:
        statement = select(FeeObligation).where(FeeObligation.id == obligation_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return await self._session.scalar(statement)

    async def obligation_for_dossier(
        self, dossier_id: UUID
    ) -> FeeObligation | None:
        return await self._session.scalar(
            select(FeeObligation).where(FeeObligation.dossier_id == dossier_id)
        )
