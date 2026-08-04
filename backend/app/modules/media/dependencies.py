from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.modules.auth.dependencies import (
    CurrentPrincipalDependency,
    SessionDependency,
    SettingsDependency,
)
from app.modules.media.gateway import CloudinaryMediaGateway
from app.modules.media.service import MediaService
from app.modules.public.rate_limit import RedisPublicRateLimiter
from app.modules.reviews.media_access import ReviewMediaAccessPolicy


async def get_media_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[MediaService]:
    secret = settings.cloudinary_api_secret
    service = MediaService(
        session=session,
        gateway=CloudinaryMediaGateway(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=secret.get_secret_value() if secret is not None else "",
            timeout_seconds=settings.media_provider_timeout_seconds,
        ),
        environment=settings.app_env,
        signature_ttl_seconds=settings.media_signature_ttl_seconds,
        delivery_ttl_seconds=settings.media_delivery_ttl_seconds,
        avatar_max_bytes=settings.media_avatar_max_bytes,
        evidence_max_bytes=settings.media_evidence_max_bytes,
        delivery_access_policy=ReviewMediaAccessPolicy(session),
    )
    try:
        yield service
    finally:
        await service.close()


MediaServiceDependency = Annotated[MediaService, Depends(get_media_service)]


async def enforce_upload_signature_rate_limit(
    principal: CurrentPrincipalDependency,
    settings: SettingsDependency,
) -> None:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        limiter = RedisPublicRateLimiter(
            redis_client,
            attempts=settings.media_upload_signature_rate_limit,
            window_seconds=settings.media_upload_signature_rate_window_seconds,
            scope="media:upload-signature:user",
        )
        await limiter.check(str(principal.user_id))
    finally:
        await redis_client.aclose()
