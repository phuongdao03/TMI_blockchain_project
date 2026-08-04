from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.ranking.public_repository import PublicRankingRepository
from app.modules.ranking.public_service import PublicRankingService
from app.modules.ranking.ranking_cache import RedisRankingCache


async def get_public_ranking_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicRankingService]:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield PublicRankingService(
            session,
            PublicRankingRepository(session),
            cache=RedisRankingCache(
                redis_client,
                ttl_seconds=settings.ranking_cache_ttl_seconds,
            ),
        )
    finally:
        await redis_client.aclose()


PublicRankingServiceDependency = Annotated[
    PublicRankingService,
    Depends(get_public_ranking_service),
]
