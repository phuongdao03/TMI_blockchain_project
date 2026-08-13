from typing import cast
from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierContentClaim,
    DossierEvidence,
    DossierStatus,
    DossierStatusHistory,
    DossierVersion,
)
from app.modules.media.models import MediaAsset
from app.modules.organizations.models import (
    MembershipStatus,
    OrganizationMember,
)


class DossierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, dossier: Dossier) -> None:
        self._session.add(dossier)

    def add_evidence(self, evidence: DossierEvidence) -> None:
        self._session.add(evidence)

    def add_version(self, version: DossierVersion) -> None:
        self._session.add(version)

    async def claim_content(
        self,
        claim: DossierContentClaim,
    ) -> DossierContentClaim:
        """Atomically claim a fingerprint, then return the winning claim."""
        bind = self._session.bind
        dialect = bind.dialect.name if bind is not None else ""
        values = {
            "id": claim.id,
            "content_fingerprint": claim.content_fingerprint,
            "dossier_id": claim.dossier_id,
            "dossier_version_id": claim.dossier_version_id,
        }
        if dialect == "postgresql":
            postgres_statement = postgres_insert(DossierContentClaim).values(values)
            postgres_statement = postgres_statement.on_conflict_do_nothing(
                index_elements=[DossierContentClaim.content_fingerprint]
            )
            await self._session.execute(postgres_statement)
        elif dialect == "sqlite":
            sqlite_statement = sqlite_insert(DossierContentClaim).values(values)
            sqlite_statement = sqlite_statement.on_conflict_do_nothing(
                index_elements=[DossierContentClaim.content_fingerprint]
            )
            await self._session.execute(sqlite_statement)
        else:
            self._session.add(claim)
            await self._session.flush()
        stored = await self.get_content_claim(
            claim.content_fingerprint,
            for_update=True,
        )
        if stored is None:
            raise RuntimeError("Content claim was not persisted.")
        return stored

    async def get_content_claim(
        self,
        fingerprint: str,
        *,
        for_update: bool = False,
    ) -> DossierContentClaim | None:
        statement = select(DossierContentClaim).where(
            DossierContentClaim.content_fingerprint == fingerprint,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            DossierContentClaim | None,
            await self._session.scalar(statement),
        )

    def add_status_history(self, history: DossierStatusHistory) -> None:
        self._session.add(history)

    async def remove_evidence(self, evidence: DossierEvidence) -> None:
        await self._session.delete(evidence)

    async def get_evidence(
        self,
        dossier_id: UUID,
        evidence_id: UUID,
        *,
        for_update: bool = False,
    ) -> DossierEvidence | None:
        statement = select(DossierEvidence).where(
            DossierEvidence.id == evidence_id,
            DossierEvidence.dossier_id == dossier_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            DossierEvidence | None,
            await self._session.scalar(statement),
        )

    async def list_draft_evidences(
        self,
        dossier_id: UUID,
    ) -> tuple[tuple[DossierEvidence, MediaAsset], ...]:
        return await self.list_evidences(dossier_id, version_id=None)

    async def list_evidences(
        self,
        dossier_id: UUID,
        *,
        version_id: UUID | None,
    ) -> tuple[tuple[DossierEvidence, MediaAsset], ...]:
        version_criterion = (
            DossierEvidence.dossier_version_id.is_(None)
            if version_id is None
            else DossierEvidence.dossier_version_id == version_id
        )
        rows = await self._session.execute(
            select(DossierEvidence, MediaAsset)
            .join(MediaAsset, MediaAsset.id == DossierEvidence.media_asset_id)
            .where(
                DossierEvidence.dossier_id == dossier_id,
                version_criterion,
            )
            .order_by(
                DossierEvidence.display_order,
                DossierEvidence.id,
            )
        )
        return tuple(rows.tuples().all())

    async def get_version(
        self,
        dossier_id: UUID,
        version_no: int,
    ) -> DossierVersion | None:
        return cast(
            DossierVersion | None,
            await self._session.scalar(
                select(DossierVersion).where(
                    DossierVersion.dossier_id == dossier_id,
                    DossierVersion.version_no == version_no,
                )
            ),
        )

    async def list_versions(
        self,
        dossier_id: UUID,
    ) -> tuple[DossierVersion, ...]:
        rows = await self._session.scalars(
            select(DossierVersion)
            .where(DossierVersion.dossier_id == dossier_id)
            .order_by(DossierVersion.version_no.desc())
        )
        return tuple(rows.all())

    async def list_status_history(
        self,
        dossier_id: UUID,
    ) -> tuple[DossierStatusHistory, ...]:
        rows = await self._session.scalars(
            select(DossierStatusHistory)
            .where(DossierStatusHistory.dossier_id == dossier_id)
            .order_by(
                DossierStatusHistory.created_at,
                DossierStatusHistory.id,
            )
        )
        return tuple(rows.all())

    async def get_category(self, category_id: UUID) -> Category | None:
        return cast(
            Category | None,
            await self._session.scalar(
                select(Category).where(
                    Category.id == category_id,
                    Category.is_active.is_(True),
                )
            ),
        )

    async def get_by_id(
        self,
        dossier_id: UUID,
        *,
        for_update: bool = False,
    ) -> Dossier | None:
        statement = select(Dossier).where(
            Dossier.id == dossier_id,
            Dossier.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(Dossier | None, await self._session.scalar(statement))

    async def list_accessible(
        self,
        user_id: UUID,
        *,
        status: DossierStatus | None,
        category_id: UUID | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[Dossier, ...], int]:
        organization_access = exists(
            select(OrganizationMember.organization_id).where(
                OrganizationMember.organization_id == Dossier.organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == MembershipStatus.ACTIVE,
            )
        )
        criteria = [
            Dossier.deleted_at.is_(None),
            or_(Dossier.owner_user_id == user_id, organization_access),
        ]
        if status is not None:
            criteria.append(Dossier.status == status)
        if category_id is not None:
            criteria.append(Dossier.category_id == category_id)

        total = await self._session.scalar(
            select(func.count()).select_from(Dossier).where(*criteria)
        )
        rows = await self._session.scalars(
            select(Dossier)
            .where(*criteria)
            .order_by(Dossier.created_at.desc(), Dossier.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return tuple(rows.all()), int(total or 0)
