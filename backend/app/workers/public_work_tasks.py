import asyncio
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.audit.service import AuditService
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.public.publication_service import PublicationService
from app.modules.public.seo_cache import RedisPublicSitemapCache
from app.modules.public.seo_service import PublicSeoService
from app.workers.celery_app import celery_app


async def _publish_scheduled() -> int:
    settings = get_settings()
    secret = settings.auth_outbox_encryption_key
    async with get_session_factory()() as session:
        service = PublicationService(
            session=session,
            audit=AuditService(session),
            payload_cipher=OutboxPayloadCipher.from_base64(
                encoded_key=secret.get_secret_value() if secret is not None else "",
                key_id=settings.auth_outbox_key_id,
            ),
        )
        return await service.publish_due(now=datetime.now(UTC), limit=100)


@celery_app.task(
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def publish_scheduled_public_works() -> int:
    return asyncio.run(_publish_scheduled())


async def _rebuild_public_sitemap() -> int:
    settings = get_settings()
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        async with get_session_factory()() as session:
            manifest = await PublicSeoService(
                session,
                cache=RedisPublicSitemapCache(
                    redis_client,
                    ttl_seconds=settings.public_sitemap_cache_ttl_seconds,
                ),
                page_size=settings.public_sitemap_page_size,
            ).rebuild()
            return manifest.total
    finally:
        await redis_client.aclose()


@celery_app.task(
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def rebuild_public_sitemap() -> int:
    return asyncio.run(_rebuild_public_sitemap())
