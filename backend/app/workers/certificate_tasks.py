import asyncio
import logging
from uuid import UUID

from sqlalchemy import and_, select

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
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
from app.modules.dossiers.models import Dossier, DossierStatus
from app.modules.media.gateway import CloudinaryMediaGateway
from app.modules.public.backfill import PublicWorkDraftBackfill
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


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


async def _repair_publication(*, batch_size: int = 100) -> None:
    """Resume issued PDFs and rebuild missing editorial drafts independently of RPC."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        candidate_ids = tuple(
            await session.scalars(
                select(Dossier.id)
                .join(Certificate, Certificate.dossier_id == Dossier.id)
                .join(
                    CertificateVersion,
                    and_(
                        CertificateVersion.certificate_id == Certificate.id,
                        CertificateVersion.version_no == Certificate.current_version_no,
                    ),
                )
                .join(
                    BlockchainTransaction,
                    BlockchainTransaction.id
                    == CertificateVersion.blockchain_transaction_id,
                )
                .where(
                    Dossier.status == DossierStatus.ANCHORED,
                    Dossier.deleted_at.is_(None),
                    Certificate.status == CertificateStatus.ACTIVE,
                    Certificate.pdf_media_id.is_not(None),
                    BlockchainTransaction.status
                    == BlockchainTransactionStatus.CONFIRMED,
                    BlockchainTransaction.tx_hash.is_not(None),
                )
                .order_by(Dossier.id)
                .limit(batch_size)
            )
        )

    for dossier_id in candidate_ids:
        try:
            await _process(dossier_id=dossier_id)
        except Exception:
            logger.exception(
                "Certificate publication recovery failed for dossier %s",
                dossier_id,
            )

    async with session_factory() as session:
        await PublicWorkDraftBackfill(session, batch_size=batch_size).run(dry_run=False)


@celery_app.task  # type: ignore[untyped-decorator]
def repair_certificate_publication() -> None:
    asyncio.run(_repair_publication())
