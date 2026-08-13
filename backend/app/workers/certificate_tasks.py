import asyncio
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.blockchain.gateway import SUPPORTED_CHAINS, BlockchainGateway
from app.modules.blockchain.nonce_lock import RedisNonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.blockchain.signer import create_transaction_signer
from app.modules.certificates.errors import CertificateGenerationError
from app.modules.certificates.metadata import (
    CertificateMetadataBuilder,
    CertificateNumberingService,
)
from app.modules.certificates.pdf import CertificatePdfRenderer
from app.modules.certificates.service import CertificateService
from app.modules.certificates.storage import CloudinaryCertificateStorage
from app.modules.media.gateway import CloudinaryMediaGateway
from app.workers.blockchain_tasks import broadcast_blockchain_transaction
from app.workers.celery_app import celery_app


async def _process(
    *,
    dossier_id: UUID | None = None,
    certificate_version_id: UUID | None = None,
) -> None:
    settings = get_settings()
    cloudinary_secret = settings.cloudinary_api_secret
    signer_secret = settings.blockchain_signer_private_key
    outbox_secret = settings.auth_outbox_encryption_key
    cloudinary_api_secret = (
        cloudinary_secret.get_secret_value() if cloudinary_secret is not None else ""
    )
    address = settings.certificate_contract_address
    gateway = BlockchainGateway(
        rpc_url=settings.blockchain_rpc_url,
        network=settings.blockchain_network,
        chain_id=settings.blockchain_chain_id,
        contract_address=address,
        abi_path=settings.blockchain_contract_abi_path,
        allowed_networks=SUPPORTED_CHAINS,
        allowed_contracts={settings.blockchain_network: {address}},
    )
    redis_client: Redis = Redis.from_url(settings.redis_url)
    signer = create_transaction_signer(
        mode=settings.blockchain_signer_mode,
        private_key=(
            signer_secret.get_secret_value() if signer_secret is not None else ""
        ),
        managed_url=settings.blockchain_managed_signer_url,
        managed_key_id=settings.blockchain_managed_signer_key_id,
        managed_expected_address=settings.blockchain_managed_signer_expected_address,
        managed_timeout_seconds=settings.blockchain_managed_signer_timeout_seconds,
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
            blockchain = BlockchainTransactionService(
                session=session,
                gateway=gateway,
                signer=signer,
                nonce_lock=RedisNonceLock(redis_client),
                network=settings.blockchain_network,
                chain_id=settings.blockchain_chain_id,
                contract_address=address,
                required_confirmations=settings.blockchain_required_confirmations,
                nonce_lock_ttl_seconds=settings.blockchain_nonce_lock_ttl_seconds,
                enqueue_broadcast=lambda transaction_id: (
                    broadcast_blockchain_transaction.delay(str(transaction_id))
                ),
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
                blockchain_service=blockchain,
            )
            if dossier_id is not None:
                await service.process_issuance(dossier_id)
            elif certificate_version_id is not None:
                await service.render_version(certificate_version_id)
            else:
                raise ValueError("A certificate operation target is required.")
    finally:
        await signer.aclose()
        await storage.close()
        await media_gateway.close()
        await gateway.close()
        await redis_client.aclose()


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
