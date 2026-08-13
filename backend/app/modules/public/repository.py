from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierStatus,
    DossierVersion,
    DossierVisibility,
)
from app.modules.public.verification import VerificationContext

PublicRow = tuple[
    Certificate,
    CertificateVersion,
    Dossier,
    Category,
    BlockchainTransaction | None,
]
PublicVersionRow = tuple[CertificateVersion, BlockchainTransaction | None]


class PublicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_assets(
        self,
        *,
        query: str | None,
        category: str | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[PublicRow, ...], int]:
        filters = self._filters(query=query, category=category)
        statement = self._public_statement().where(*filters)
        rows = (
            await self._session.execute(
                statement.order_by(Dossier.published_at.desc(), Dossier.title)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        total = await self._session.scalar(
            select(func.count())
            .select_from(Certificate)
            .join(Dossier, Dossier.id == Certificate.dossier_id)
            .join(Category, Category.id == Dossier.category_id)
            .where(*filters)
        )
        return tuple(cast(PublicRow, row) for row in rows), int(total or 0)

    async def get_asset(self, slug: str) -> PublicRow | None:
        row = (
            await self._session.execute(
                self._public_statement().where(Dossier.slug == slug)
            )
        ).one_or_none()
        return cast(PublicRow | None, row)

    async def list_categories(self) -> Sequence[tuple[Category, int]]:
        count = func.count(Certificate.id)
        rows = (
            await self._session.execute(
                select(Category, count)
                .outerjoin(
                    Dossier,
                    (Dossier.category_id == Category.id) & self._published_condition(),
                )
                .outerjoin(Certificate, Certificate.dossier_id == Dossier.id)
                .where(Category.is_active.is_(True))
                .group_by(Category.id)
                .order_by(Category.display_order, Category.name)
            )
        ).all()
        return tuple((row[0], row[1]) for row in rows)

    async def find_by_token(self, token_hash: str) -> VerificationContext | None:
        return await self._verification_context(
            Certificate.public_token_hash == token_hash
        )

    async def find_by_number(self, number: str) -> VerificationContext | None:
        return await self._verification_context(
            Certificate.certificate_number == number
        )

    async def find_by_transaction(
        self,
        transaction_hash: str,
    ) -> VerificationContext | None:
        return await self._verification_context(
            func.lower(BlockchainTransaction.tx_hash) == transaction_hash
        )

    async def list_certificate_versions(
        self,
        certificate_number: str,
    ) -> tuple[PublicVersionRow, ...]:
        rows = await self._session.execute(
            select(CertificateVersion, BlockchainTransaction)
            .join(Certificate, Certificate.id == CertificateVersion.certificate_id)
            .join(Dossier, Dossier.id == Certificate.dossier_id)
            .outerjoin(
                BlockchainTransaction,
                BlockchainTransaction.id
                == CertificateVersion.blockchain_transaction_id,
            )
            .where(
                Certificate.certificate_number == certificate_number,
                self._published_condition(),
                CertificateVersion.status.in_(
                    (
                        CertificateVersionStatus.ACTIVE,
                        CertificateVersionStatus.SUPERSEDED,
                        CertificateVersionStatus.REVOKED,
                    )
                ),
                BlockchainTransaction.status
                == BlockchainTransactionStatus.CONFIRMED,
            )
            .order_by(CertificateVersion.version_no.desc())
        )
        return tuple(cast(PublicVersionRow, row) for row in rows.all())

    async def _verification_context(
        self,
        condition: ColumnElement[bool],
    ) -> VerificationContext | None:
        row = (
            await self._session.execute(
                self._public_statement()
                .add_columns(
                    DossierVersion.canonical_hash,
                    DossierVersion.snapshot_json,
                )
                .join(
                    DossierVersion,
                    DossierVersion.id == CertificateVersion.dossier_version_id,
                )
                .where(condition)
            )
        ).one_or_none()
        if row is None:
            return None
        (
            certificate,
            version,
            dossier,
            category,
            transaction,
            dossier_hash,
            dossier_snapshot,
        ) = row
        return VerificationContext(
            certificate_id=certificate.id,
            certificate_number=certificate.certificate_number,
            certificate_status=certificate.status,
            asset_title=dossier.title,
            category_name=category.name,
            issued_at=certificate.issued_at,
            expires_at=certificate.expires_at,
            metadata_hash=version.metadata_hash,
            dossier_hash=dossier_hash,
            metadata=dict(version.metadata_json),
            dossier_snapshot=dict(dossier_snapshot),
            version=version.version_no,
            network=transaction.network if transaction is not None else None,
            contract_address=(
                transaction.contract_address if transaction is not None else None
            ),
            transaction_hash=(transaction.tx_hash if transaction is not None else None),
            confirmations=(transaction.confirmations if transaction is not None else 0),
            confirmed_at=(
                transaction.confirmed_at if transaction is not None else None
            ),
            dossier_code=dossier.code,
            block_number=(
                transaction.receipt_block_number
                if transaction is not None
                else None
            ),
        )

    @staticmethod
    def _filters(
        *,
        query: str | None,
        category: str | None,
    ) -> list[ColumnElement[bool]]:
        filters = [PublicRepository._published_condition()]
        if query:
            pattern = f"%{query.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Dossier.title).like(pattern),
                    func.lower(Dossier.code).like(pattern),
                    func.lower(Certificate.certificate_number).like(pattern),
                )
            )
        if category:
            filters.append(func.lower(Category.code) == category.strip().lower())
        return filters

    @staticmethod
    def _published_condition() -> ColumnElement[bool]:
        return (
            (Dossier.status == DossierStatus.PUBLISHED)
            & (Dossier.visibility == DossierVisibility.PUBLIC)
            & Dossier.slug.is_not(None)
            & Dossier.deleted_at.is_(None)
        )

    @staticmethod
    def _public_statement() -> Select[
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
