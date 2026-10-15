from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.community.admin_service import CommunityAdminService
from app.modules.community.engagement_service import CommunityEngagementService
from app.modules.community.media_delivery import CommunityMediaDeliveryService
from app.modules.community.service import CommunityService
from app.modules.engagement.redis import RedisViewDeduplicator
from app.modules.engagement.visitor import EngagementVisitorContext
from app.modules.media.dependencies import MediaServiceDependency


async def get_community_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> CommunityService:
    return CommunityService(
        session,
        image_max_count=settings.community_post_image_max_count,
        image_max_bytes=settings.community_post_image_max_bytes,
    )


CommunityServiceDependency = Annotated[
    CommunityService,
    Depends(get_community_service),
]


async def get_community_media_delivery_service(
    session: SessionDependency,
    media_service: MediaServiceDependency,
    settings: SettingsDependency,
) -> CommunityMediaDeliveryService:
    return CommunityMediaDeliveryService(
        session,
        media_service,
        image_max_bytes=settings.community_post_image_max_bytes,
        avatar_max_bytes=settings.media_avatar_max_bytes,
    )


CommunityMediaDeliveryServiceDependency = Annotated[
    CommunityMediaDeliveryService,
    Depends(get_community_media_delivery_service),
]


async def get_community_engagement_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[CommunityEngagementService]:
    secret = settings.engagement_visitor_hmac_secret
    if secret is None:
        yield CommunityEngagementService(
            session,
            avatar_max_bytes=settings.media_avatar_max_bytes,
        )
        return
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield CommunityEngagementService(
            session,
            avatar_max_bytes=settings.media_avatar_max_bytes,
            views=RedisViewDeduplicator(
                redis_client,
                visitor_context=EngagementVisitorContext(
                    secret=secret.get_secret_value(),
                ),
                ttl_seconds=settings.engagement_view_dedupe_ttl_seconds,
                scope="community:post:view",
            ),
        )
    finally:
        await redis_client.aclose()


CommunityEngagementServiceDependency = Annotated[
    CommunityEngagementService,
    Depends(get_community_engagement_service),
]


async def get_community_admin_service(
    session: SessionDependency,
) -> CommunityAdminService:
    return CommunityAdminService(session)


CommunityAdminServiceDependency = Annotated[
    CommunityAdminService,
    Depends(get_community_admin_service),
]
