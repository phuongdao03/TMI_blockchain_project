import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
    CertificateVersion,
)
from app.modules.dossiers.models import (
    Dossier,
    DossierEvidence,
    DossierStatus,
    DossierVersion,
    EvidenceVisibility,
)
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.models import (
    PublicationStatus,
    PublicMediaKind,
    PublicWork,
    PublicWorkMedia,
    PublicWorkVisibility,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_SLUGS = frozenset(
    {
        "admin",
        "api",
        "login",
        "register",
        "search",
        "sitemap",
        "verify",
    }
)
PUBLIC_EVIDENCE_SCOPES = (
    EvidenceVisibility.PUBLIC,
    EvidenceVisibility.PUBLIC_PREVIEW,
)
PUBLIC_MEDIA_KINDS = {
    "image/jpeg": PublicMediaKind.IMAGE,
    "image/png": PublicMediaKind.IMAGE,
    "image/webp": PublicMediaKind.IMAGE,
    "audio/mpeg": PublicMediaKind.AUDIO,
    "audio/mp4": PublicMediaKind.AUDIO,
    "audio/ogg": PublicMediaKind.AUDIO,
    "video/mp4": PublicMediaKind.VIDEO,
    "video/webm": PublicMediaKind.VIDEO,
    "application/pdf": PublicMediaKind.DOCUMENT,
}


@dataclass(frozen=True, slots=True)
class PublicWorkBackfillReport:
    scanned: int
    eligible: int
    created: int
    skipped: int
    skip_reasons: dict[str, int]


class PublicWorkDraftBackfill:
    def __init__(self, session: AsyncSession, *, batch_size: int = 500) -> None:
        if batch_size < 1 or batch_size > 5_000:
            raise ValueError("batch_size must be between 1 and 5000")
        self._session = session
        self._repository = PublicWorkRepository(session)
        self._batch_size = batch_size

    async def run(self, *, dry_run: bool = True) -> PublicWorkBackfillReport:
        if self._session.in_transaction():
            return await self._run(dry_run=dry_run)
        async with self._session.begin():
            return await self._run(dry_run=dry_run)

    async def ensure_draft(
        self,
        dossier_id: UUID,
        *,
        certificate_id: UUID | None,
    ) -> PublicWork | None:
        """Create or repair the single private editorial draft for a dossier.

        This is safe to call from the certificate worker and from a replay.
        It deliberately creates a private draft; publication remains an
        explicit content-administration decision.
        """
        if self._session.in_transaction():
            return await self._ensure_draft(
                dossier_id,
                certificate_id=certificate_id,
            )
        async with self._session.begin():
            return await self._ensure_draft(
                dossier_id,
                certificate_id=certificate_id,
            )

    async def _ensure_draft(
        self,
        dossier_id: UUID,
        *,
        certificate_id: UUID | None,
    ) -> PublicWork | None:
        existing = await self._repository.get_by_dossier_id(dossier_id)
        if existing is not None:
            if existing.certificate_id is None and certificate_id is not None:
                existing.certificate_id = certificate_id
            await self._sync_public_evidence(existing, certificate_id=certificate_id)
            return existing
        dossier = await self._session.get(Dossier, dossier_id)
        if dossier is None:
            return None
        draft, _ = await self._draft_from_source(
            dossier,
            certificate_id=certificate_id,
            reserved_in_batch=set(),
        )
        if draft is None:
            return None
        self._repository.add(draft)
        await self._session.flush()
        await self._sync_public_evidence(draft, certificate_id=certificate_id)
        return draft

    async def _run(self, *, dry_run: bool) -> PublicWorkBackfillReport:
        reasons: Counter[str] = Counter()
        reserved_in_batch: set[str] = set()
        cursor = None
        scanned = 0
        eligible = 0
        while True:
            sources = await self._repository.list_backfill_sources(
                after=cursor,
                limit=self._batch_size,
            )
            if not sources:
                break
            scanned += len(sources)
            for source in sources:
                draft, reason = await self._draft_from_source(
                    source.dossier,
                    certificate_id=source.certificate_id,
                    reserved_in_batch=reserved_in_batch,
                )
                if draft is None:
                    reasons[reason or "invalid_legacy_data"] += 1
                    continue
                eligible += 1
                reserved_in_batch.add(draft.slug)
                if not dry_run:
                    self._repository.add(draft)
                    await self._session.flush()
                    await self._sync_public_evidence(
                        draft,
                        certificate_id=source.certificate_id,
                    )
            if not dry_run:
                await self._session.flush()
            last_dossier = sources[-1].dossier
            cursor = last_dossier.id

        if not dry_run:
            await self._sync_existing_drafts()

        return PublicWorkBackfillReport(
            scanned=scanned,
            eligible=eligible,
            created=0 if dry_run else eligible,
            skipped=sum(reasons.values()),
            skip_reasons=dict(sorted(reasons.items())),
        )

    async def _sync_existing_drafts(self) -> None:
        cursor: UUID | None = None
        while True:
            latest_certificate_id = (
                select(Certificate.id)
                .where(Certificate.dossier_id == PublicWork.dossier_id)
                .order_by(Certificate.issued_at.desc(), Certificate.id.desc())
                .limit(1)
                .scalar_subquery()
            )
            confirmed_current_proof = exists(
                select(BlockchainTransaction.id)
                .join(
                    DossierVersion,
                    DossierVersion.id == BlockchainTransaction.dossier_version_id,
                )
                .where(
                    BlockchainTransaction.dossier_id == PublicWork.dossier_id,
                    DossierVersion.dossier_id == PublicWork.dossier_id,
                    DossierVersion.version_no == Dossier.current_version_no,
                    BlockchainTransaction.method.in_(
                        ("recordProof", "issueCertificate")
                    ),
                    BlockchainTransaction.status
                    == BlockchainTransactionStatus.CONFIRMED,
                    BlockchainTransaction.tx_hash.is_not(None),
                )
            )
            statement = (
                select(
                    PublicWork,
                    latest_certificate_id.label("latest_certificate_id"),
                )
                .join(Dossier, Dossier.id == PublicWork.dossier_id)
                .where(
                    or_(
                        Dossier.status.in_(
                            (
                                DossierStatus.CERTIFICATE_ISSUED,
                                DossierStatus.PUBLISHED,
                            )
                        ),
                        confirmed_current_proof,
                    ),
                    PublicWork.deleted_at.is_(None),
                )
                .order_by(PublicWork.id)
                .limit(self._batch_size)
            )
            if cursor is not None:
                statement = statement.where(PublicWork.id > cursor)
            rows = tuple((await self._session.execute(statement)).tuples())
            if not rows:
                break
            for work, certificate_id in rows:
                if work.certificate_id is None and certificate_id is not None:
                    work.certificate_id = certificate_id
                await self._sync_public_evidence(
                    work,
                    certificate_id=work.certificate_id,
                )
            await self._session.flush()
            cursor = rows[-1][0].id

    async def _sync_public_evidence(
        self,
        work: PublicWork,
        *,
        certificate_id: UUID | None,
    ) -> None:
        certificate = (
            await self._session.get(Certificate, certificate_id)
            if certificate_id is not None
            else None
        )
        version_id = None
        if certificate is not None and certificate.status is CertificateStatus.ACTIVE:
            version_id = await self._session.scalar(
                select(CertificateVersion.dossier_version_id).where(
                    CertificateVersion.certificate_id == certificate.id,
                    CertificateVersion.version_no == certificate.current_version_no,
                )
            )
        if version_id is None:
            version_id = await self._session.scalar(
                select(DossierVersion.id)
                .join(Dossier, Dossier.id == DossierVersion.dossier_id)
                .where(
                    DossierVersion.dossier_id == work.dossier_id,
                    DossierVersion.version_no == Dossier.current_version_no,
                )
            )
        if version_id is None:
            return
        existing_ids = set(
            await self._session.scalars(
                select(PublicWorkMedia.media_asset_id).where(
                    PublicWorkMedia.public_work_id == work.id
                )
            )
        )
        rows = await self._session.execute(
            select(DossierEvidence, MediaAsset)
            .join(MediaAsset, MediaAsset.id == DossierEvidence.media_asset_id)
            .where(
                DossierEvidence.dossier_id == work.dossier_id,
                DossierEvidence.dossier_version_id == version_id,
                or_(
                    DossierEvidence.access_scope.in_(PUBLIC_EVIDENCE_SCOPES),
                    DossierEvidence.evidence_role == "PRIMARY_WORK",
                ),
                MediaAsset.status == MediaStatus.ACTIVE,
                MediaAsset.deleted_at.is_(None),
            )
            .order_by(DossierEvidence.display_order, DossierEvidence.id)
        )
        for evidence, asset in rows.tuples():
            kind = PUBLIC_MEDIA_KINDS.get(asset.mime_type)
            if kind is None or asset.id in existing_ids:
                continue
            self._session.add(
                PublicWorkMedia(
                    public_work_id=work.id,
                    media_asset_id=asset.id,
                    media_kind=kind,
                    sort_order=evidence.display_order,
                    caption=evidence.title,
                    alt_text=evidence.title if kind is PublicMediaKind.IMAGE else None,
                )
            )
            existing_ids.add(asset.id)

    async def _draft_from_source(
        self,
        dossier: Dossier,
        *,
        certificate_id: UUID | None,
        reserved_in_batch: set[str],
    ) -> tuple[PublicWork | None, str | None]:
        title = dossier.title.strip()
        if not title:
            return None, "missing_public_title"
        description = (dossier.summary or "").strip() or title
        slug = await self._available_slug(dossier, reserved_in_batch)
        if slug is None:
            return None, "invalid_public_slug"
        return (
            PublicWork(
                dossier_id=dossier.id,
                certificate_id=certificate_id,
                owner_user_id=dossier.owner_user_id,
                organization_id=dossier.organization_id,
                slug=slug,
                title=title,
                short_description=description[:500],
                full_description=None,
                publication_status=PublicationStatus.DRAFT,
                visibility=PublicWorkVisibility.PRIVATE,
                author_display_name=None,
                category_id=dossier.category_id,
                thumbnail_media_id=None,
                published_at=None,
            ),
            None,
        )

    async def _available_slug(
        self,
        dossier: Dossier,
        reserved_in_batch: set[str],
    ) -> str | None:
        preferred = (dossier.slug or "").strip().lower()
        if not self._valid_slug(preferred):
            preferred = self._slugify(dossier.title)
        candidates = (
            preferred,
            f"{preferred}-{self._slugify(dossier.code)}" if preferred else "",
        )
        for candidate in candidates:
            candidate = candidate[:180].rstrip("-")
            if (
                self._valid_slug(candidate)
                and candidate not in reserved_in_batch
                and not await self._repository.slug_exists(candidate)
            ):
                return candidate
        return None

    @staticmethod
    def _valid_slug(slug: str) -> bool:
        return (
            0 < len(slug) <= 180
            and slug not in RESERVED_SLUGS
            and SLUG_PATTERN.fullmatch(slug) is not None
        )

    @staticmethod
    def _slugify(value: str) -> str:
        ascii_value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
