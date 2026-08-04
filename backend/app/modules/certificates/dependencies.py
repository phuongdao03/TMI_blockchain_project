from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.blockchain.dependencies import BlockchainServiceDependency
from app.modules.certificates.metadata import (
    CertificateMetadataBuilder,
    CertificateNumberingService,
)
from app.modules.certificates.pdf import CertificatePdfRenderer
from app.modules.certificates.service import CertificateService
from app.modules.certificates.storage import CloudinaryCertificateStorage
from app.modules.media.gateway import CloudinaryMediaGateway
from app.workers.certificate_tasks import issue_certificate


async def get_certificate_service(
    session: SessionDependency,
    settings: SettingsDependency,
    blockchain_service: BlockchainServiceDependency,
) -> AsyncIterator[CertificateService]:
    cloudinary_secret = settings.cloudinary_api_secret
    outbox_secret = settings.auth_outbox_encryption_key
    cloudinary_api_secret = (
        cloudinary_secret.get_secret_value()
        if cloudinary_secret is not None
        else ""
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
        blockchain_service=blockchain_service,
        enqueue_issue=lambda dossier_id: issue_certificate.delay(str(dossier_id)),
    )
    try:
        yield service
    finally:
        await media_gateway.close()
        await storage.close()


CertificateServiceDependency = Annotated[
    CertificateService,
    Depends(get_certificate_service),
]
