from typing import cast
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    BlockchainTransaction,
    Certificate,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.dossiers.models import Category, Dossier
from app.modules.organizations.models import (
    MembershipStatus,
    OrganizationMember,
)
from app.modules.public.models import PublicationStatus, PublicWork

CertificateRow = tuple[
    Certificate,
    CertificateVersion,
    Dossier,
    Category,
    BlockchainTransaction | None,
]
AdminCertificateRow = tuple[
    Certificate,
    CertificateVersion,
    Dossier,
    Category,
    BlockchainTransaction | None,
    PublicWork | None,
]


class CertificateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, certificate: Certificate) -> None:
        self._session.add(certificate)

    def add_version(self, version: CertificateVersion) -> None:
        self._session.add(version)

    async def get_version(
        self,
        version_id: UUID,
        *,
        for_update: bool = False,
    ) -> CertificateVersion | None:
        statement = select(CertificateVersion).where(
            CertificateVersion.id == version_id
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            CertificateVersion | None,
            await self._session.scalar(statement),
        )

    async def get_open_version_request(
        self,
        certificate_id: UUID,
    ) -> CertificateVersion | None:
        return cast(
            CertificateVersion | None,
            await self._session.scalar(
                select(CertificateVersion).where(
                    CertificateVersion.certificate_id == certificate_id,
                    CertificateVersion.status.in_(
                        (
                            CertificateVersionStatus.PENDING_APPROVAL,
                            CertificateVersionStatus.ANCHOR_PENDING,
                            CertificateVersionStatus.FAILED,
                        )
                    ),
                )
            ),
        )

    async def list_versions(
        self,
        certificate_id: UUID,
    ) -> tuple[CertificateVersion, ...]:
        rows = await self._session.scalars(
            select(CertificateVersion)
            .where(CertificateVersion.certificate_id == certificate_id)
            .order_by(CertificateVersion.version_no.desc())
        )
        return tuple(rows.all())

    async def list_version_requests(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CertificateVersion, ...], int]:
        criteria = CertificateVersion.status.in_(
            (
                CertificateVersionStatus.PENDING_APPROVAL,
                CertificateVersionStatus.ANCHOR_PENDING,
                CertificateVersionStatus.FAILED,
            )
        )
        rows = await self._session.scalars(
            select(CertificateVersion)
            .where(criteria)
            .order_by(CertificateVersion.requested_at, CertificateVersion.id)
            .offset(offset)
            .limit(limit)
        )
        total = await self._session.scalar(
            select(func.count()).select_from(CertificateVersion).where(criteria)
        )
        return tuple(rows.all()), int(total or 0)

    async def get_by_dossier(
        self,
        dossier_id: UUID,
        *,
        for_update: bool = False,
    ) -> Certificate | None:
        statement = select(Certificate).where(Certificate.dossier_id == dossier_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(Certificate | None, await self._session.scalar(statement))

    async def get(self, certificate_id: UUID) -> CertificateRow | None:
        row = (
            await self._session.execute(
                self._detail_statement().where(Certificate.id == certificate_id)
            )
        ).one_or_none()
        return cast(CertificateRow | None, row)

    async def list_accessible(
        self,
        user_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CertificateRow, ...], int]:
        membership = (
            select(OrganizationMember.organization_id)
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == MembershipStatus.ACTIVE,
            )
            .scalar_subquery()
        )
        condition = or_(
            Dossier.owner_user_id == user_id,
            Dossier.organization_id.in_(membership),
        )
        statement = self._detail_statement().where(condition)
        rows = (
            await self._session.execute(
                statement.order_by(Certificate.issued_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
        total = await self._session.scalar(
            select(func.count())
            .select_from(Certificate)
            .join(Dossier, Dossier.id == Certificate.dossier_id)
            .where(condition)
        )
        return tuple(cast(CertificateRow, row) for row in rows), int(total or 0)

    async def list_admin(
        self,
        *,
        search: str | None,
        status: str | None,
        publication_status: PublicationStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[AdminCertificateRow, ...], int]:
        filters = []
        if search:
            escaped = (
                search.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    Certificate.certificate_number.ilike(pattern, escape="\\"),
                    Dossier.code.ilike(pattern, escape="\\"),
                    Dossier.title.ilike(pattern, escape="\\"),
                )
            )
        if status:
            filters.append(Certificate.status == status)
        if publication_status:
            filters.append(PublicWork.publication_status == publication_status)
        statement = self._admin_statement().where(*filters)
        rows = (
            await self._session.execute(
                statement.order_by(Certificate.issued_at.desc(), Certificate.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        total = await self._session.scalar(
            select(func.count())
            .select_from(Certificate)
            .join(Dossier, Dossier.id == Certificate.dossier_id)
            .outerjoin(PublicWork, PublicWork.certificate_id == Certificate.id)
            .where(*filters)
        )
        return tuple(cast(AdminCertificateRow, row) for row in rows), int(total or 0)

    async def can_access(self, certificate_id: UUID, user_id: UUID) -> bool:
        membership = (
            select(OrganizationMember.organization_id)
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == MembershipStatus.ACTIVE,
            )
            .scalar_subquery()
        )
        count = await self._session.scalar(
            select(func.count())
            .select_from(Certificate)
            .join(Dossier, Dossier.id == Certificate.dossier_id)
            .where(
                Certificate.id == certificate_id,
                or_(
                    Dossier.owner_user_id == user_id,
                    Dossier.organization_id.in_(membership),
                ),
            )
        )
        return bool(count)

    @staticmethod
    def _detail_statement() -> Select[
        tuple[
            Certificate,
            CertificateVersion,
            Dossier,
            Category,
            BlockchainTransaction,
        ]
    ]:
        return (
            select(
                Certificate,
                CertificateVersion,
                Dossier,
                Category,
                BlockchainTransaction,
            )
            .join(Dossier, Dossier.id == Certificate.dossier_id)
            .join(Category, Category.id == Dossier.category_id)
            .join(
                CertificateVersion,
                (CertificateVersion.certificate_id == Certificate.id)
                & (CertificateVersion.version_no == Certificate.current_version_no),
            )
            .outerjoin(
                BlockchainTransaction,
                BlockchainTransaction.id
                == CertificateVersion.blockchain_transaction_id,
            )
        )

    @staticmethod
    def _admin_statement() -> Select:
        return (
            CertificateRepository._detail_statement()
            .add_columns(PublicWork)
            .outerjoin(PublicWork, PublicWork.certificate_id == Certificate.id)
        )
