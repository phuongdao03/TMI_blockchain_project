from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.search.discovery_cache import RedisDiscoveryCache
from app.modules.search.discovery_repository import SearchDiscoveryRepository
from app.modules.search.discovery_service import SearchDiscoveryService


async def get_search_discovery_service(
    session: SessionDependency, settings: SettingsDependency
) -> AsyncIterator[SearchDiscoveryService]:
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    try:
        yield SearchDiscoveryService(
            SearchDiscoveryRepository(session),
            cache=RedisDiscoveryCache(
                redis_client, ttl_seconds=settings.public_catalog_cache_ttl_seconds
            ),
            audit=AuditService(session),
            minimum_trending_count=settings.search_trending_minimum_count,
        )
    finally:
        await redis_client.aclose()


SearchDiscoveryDependency = Annotated[
    SearchDiscoveryService, Depends(get_search_discovery_service)
]
