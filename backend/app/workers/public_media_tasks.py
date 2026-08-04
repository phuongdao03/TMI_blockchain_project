import asyncio
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.media.errors import MediaProviderUnavailableError
from app.modules.media.gateway import CloudinaryMediaGateway
from app.modules.public.media_service import PublicMediaWorker
from app.workers.celery_app import celery_app


async def _generate(relation_id: UUID) -> None:
    settings = get_settings()
    secret = settings.cloudinary_api_secret
    gateway = CloudinaryMediaGateway(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=secret.get_secret_value() if secret is not None else "",
        timeout_seconds=settings.media_provider_timeout_seconds,
    )
    try:
        async with get_session_factory()() as session:
            worker = PublicMediaWorker(
                session=session,
                gateway=gateway,
                environment=settings.app_env,
                payload_cipher=OutboxPayloadCipher.from_base64(
                    encoded_key=(
                        settings.auth_outbox_encryption_key.get_secret_value()
                        if settings.auth_outbox_encryption_key is not None
                        else ""
                    ),
                    key_id=settings.auth_outbox_key_id,
                ),
            )
            await worker.process(relation_id)
    finally:
        await gateway.close()


@celery_app.task(
    autoretry_for=(OperationalError, MediaProviderUnavailableError),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def generate_public_media_derivative(relation_id: str) -> None:
    asyncio.run(_generate(UUID(relation_id)))
