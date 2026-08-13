import asyncio
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.media.encryption import DocumentEncryptionKeyring
from app.modules.media.errors import MediaProviderUnavailableError
from app.modules.media.gateway import CloudinaryMediaGateway
from app.modules.media.inspection import (
    ClamAvScanner,
    InspectionUnavailableError,
    MediaInspectionService,
)
from app.modules.media.repository import MediaAssetRepository
from app.workers.celery_app import celery_app


def _document_keyring() -> DocumentEncryptionKeyring | None:
    settings = get_settings()
    if not settings.media_private_encryption_enabled:
        return None
    return DocumentEncryptionKeyring.from_base64_keys(
        active_key_id=settings.media_private_encryption_active_key_id,
        encoded_keys={
            key_id: secret.get_secret_value()
            for key_id, secret in settings.media_private_encryption_keys.items()
        },
    )


async def _inspect(media_id: UUID) -> None:
    settings = get_settings()
    secret = settings.cloudinary_api_secret
    gateway = CloudinaryMediaGateway(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=secret.get_secret_value() if secret is not None else "",
        timeout_seconds=settings.media_provider_timeout_seconds,
    )
    scanner = ClamAvScanner(
        host=settings.media_scanner_host,
        port=settings.media_scanner_port,
        timeout_seconds=settings.media_scanner_timeout_seconds,
    )
    try:
        async with get_session_factory()() as session:
            service = MediaInspectionService(
                session=session,
                gateway=gateway,
                scanner=scanner,
                max_attempts=settings.media_inspection_max_attempts,
                encryption_keyring=_document_keyring(),
                private_encryption_required=(settings.media_private_encryption_enabled),
            )
            await service.inspect(media_id)
    finally:
        await gateway.close()


async def _reverify(media_id: UUID) -> None:
    settings = get_settings()
    secret = settings.cloudinary_api_secret
    gateway = CloudinaryMediaGateway(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=secret.get_secret_value() if secret is not None else "",
        timeout_seconds=settings.media_provider_timeout_seconds,
    )
    scanner = ClamAvScanner(
        host=settings.media_scanner_host,
        port=settings.media_scanner_port,
        timeout_seconds=settings.media_scanner_timeout_seconds,
    )
    try:
        async with get_session_factory()() as session:
            service = MediaInspectionService(
                session=session,
                gateway=gateway,
                scanner=scanner,
                max_attempts=settings.media_inspection_max_attempts,
                encryption_keyring=_document_keyring(),
                private_encryption_required=(settings.media_private_encryption_enabled),
            )
            await service.reverify(media_id)
    finally:
        await gateway.close()


async def _enqueue_provenance_backfill() -> None:
    async with get_session_factory()() as session:
        repository = MediaAssetRepository(session)
        media_ids = await repository.list_untrusted_active_ids(limit=25)
        legacy_private_ids = await repository.list_legacy_private_ids(limit=25)
    for media_id in media_ids:
        reverify_media_asset.delay(str(media_id))
    for media_id in legacy_private_ids:
        inspect_media_asset.delay(str(media_id))


@celery_app.task(
    name="app.workers.media_inspection_tasks.inspect_media_asset",
    autoretry_for=(
        OperationalError,
        MediaProviderUnavailableError,
        InspectionUnavailableError,
    ),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def inspect_media_asset(media_id: str) -> None:
    asyncio.run(_inspect(UUID(media_id)))


@celery_app.task(
    name="app.workers.media_inspection_tasks.reverify_media_asset",
    autoretry_for=(
        OperationalError,
        MediaProviderUnavailableError,
        InspectionUnavailableError,
    ),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def reverify_media_asset(media_id: str) -> None:
    asyncio.run(_reverify(UUID(media_id)))


@celery_app.task(
    name="app.workers.media_inspection_tasks.backfill_media_provenance",
)  # type: ignore[untyped-decorator]
def backfill_media_provenance() -> None:
    asyncio.run(_enqueue_provenance_backfill())
