import asyncio
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateVersion,
)
from app.modules.certificates.errors import CertificateGenerationError
from app.modules.certificates.metadata import (
    CertificateMetadataBuilder,
    CertificateNumberingService,
)
from app.modules.certificates.pdf import CertificatePdfRenderer
from app.modules.certificates.service import CertificateService
from app.modules.certificates.storage import CloudinaryCertificateStorage
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVersion
from app.modules.media.gateway import CloudinaryMediaGateway
from app.modules.public.backfill import PublicWorkDraftBackfill
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PublicationRecoveryReport:
    candidates: int
    recovered: int
    failed: int


async def _process(
    *,
    dossier_id: UUID | None = None,
    certificate_version_id: UUID | None = None,
) -> None:
    settings = get_settings()
    cloudinary_secret = settings.cloudinary_api_secret
    outbox_secret = settings.auth_outbox_encryption_key
    cloudinary_api_secret = (
        cloudinary_secret.get_secret_value() if cloudinary_secret is not None else ""
    )
    media_gateway = CloudinaryMediaGateway(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=cloudinary_api_secret,
        timeout_seconds=settings.media_provider_timeout_seconds,
    )
    storage = CloudinaryCertificateStorage(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=cloudinary_api_secret,
        timeout_seconds=settings.media_provider_timeout_seconds,
    )
    try:
        async with get_session_factory()() as session:
            service = CertificateService(
                session=session,
                media_gateway=media_gateway,
                storage=storage,
                renderer=CertificatePdfRenderer(
                    template_version=settings.certificate_template_version,
                    generator_version="reportlab-5.0.0",
                ),
                metadata_builder=CertificateMetadataBuilder(),
                numbering=CertificateNumberingService(),
                payload_cipher=OutboxPayloadCipher.from_base64(
                    encoded_key=(
                        outbox_secret.get_secret_value()
                        if outbox_secret is not None
                        else ""
                    ),
                    key_id=settings.auth_outbox_key_id,
                ),
                public_base_url=settings.app_base_url,
                environment=settings.app_env,
                delivery_ttl_seconds=settings.media_delivery_ttl_seconds,
                validity_days=settings.certificate_validity_days,
            )
            if dossier_id is not None:
                await service.process_issuance(dossier_id)
            elif certificate_version_id is not None:
                await service.render_version(certificate_version_id)
            else:
                raise ValueError("A certificate operation target is required.")
    finally:
        await storage.close()
        await media_gateway.close()


@celery_app.task(
    autoretry_for=(CertificateGenerationError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def issue_certificate(dossier_id: str) -> None:
    asyncio.run(_process(dossier_id=UUID(dossier_id)))


@celery_app.task(
    autoretry_for=(CertificateGenerationError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def render_certificate_version(certificate_version_id: str) -> None:
    asyncio.run(_process(certificate_version_id=UUID(certificate_version_id)))


async def _repair_publication(*, batch_size: int = 100) -> PublicationRecoveryReport:
    """Resume issued PDFs and rebuild missing editorial drafts independently of RPC."""
    session_factory = get_session_factory()
    candidates = 0
    recovered = 0
    failed = 0
    cursor: UUID | None = None
    while True:
        async with session_factory() as session:
            candidate_ids = await _publication_recovery_candidate_ids(
                session,
                batch_size=batch_size,
                after=cursor,
            )
        if not candidate_ids:
            break
        candidates += len(candidate_ids)
        for dossier_id in candidate_ids:
            try:
                await _process(dossier_id=dossier_id)
                recovered += 1
            except Exception:
                failed += 1
                logger.exception(
                    "Certificate publication recovery failed for dossier %s",
                    dossier_id,
                )
        cursor = candidate_ids[-1]

    async with session_factory() as session:
        await PublicWorkDraftBackfill(session, batch_size=batch_size).run(dry_run=False)
    return PublicationRecoveryReport(
        candidates=candidates,
        recovered=recovered,
        failed=failed,
    )


async def _publication_recovery_candidate_ids(
    session: AsyncSession,
    *,
    batch_size: int,
    after: UUID | None = None,
) -> tuple[UUID, ...]:
    """Return current dossiers whose confirmed proof issuance can be resumed."""
    return tuple(
        await session.scalars(
            select(Dossier.id)
            .join(
                DossierVersion,
                and_(
                    DossierVersion.dossier_id == Dossier.id,
                    DossierVersion.version_no == Dossier.current_version_no,
                ),
            )
            .join(
                BlockchainTransaction,
                and_(
                    BlockchainTransaction.dossier_version_id == DossierVersion.id,
                    or_(
                        BlockchainTransaction.method == "recordProof",
                        exists(
                            select(CertificateVersion.id)
                            .join(
                                Certificate,
                                Certificate.id == CertificateVersion.certificate_id,
                            )
                            .where(
                                Certificate.dossier_id == Dossier.id,
                                CertificateVersion.version_no
                                == Certificate.current_version_no,
                                CertificateVersion.blockchain_transaction_id
                                == BlockchainTransaction.id,
                            )
                        ),
                    ),
                ),
            )
            .where(
                Dossier.status.in_((DossierStatus.PAID, DossierStatus.ANCHORED)),
                Dossier.deleted_at.is_(None),
                BlockchainTransaction.status == BlockchainTransactionStatus.CONFIRMED,
                BlockchainTransaction.tx_hash.is_not(None),
                *((Dossier.id > after,) if after is not None else ()),
            )
            .distinct()
            .order_by(Dossier.id)
            .limit(batch_size)
        )
    )


@celery_app.task  # type: ignore[untyped-decorator]
def repair_certificate_publication() -> None:
    asyncio.run(_repair_publication())
