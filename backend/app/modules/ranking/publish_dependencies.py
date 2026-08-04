from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.ranking.publish import RankingPublicationService
from app.modules.ranking.publish_repository import RankingPublicationRepository
from app.modules.ranking.ranking_cache import RedisRankingCache


async def get_ranking_publication_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[RankingPublicationService]:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield RankingPublicationService(
            RankingPublicationRepository(session),
            audit=AuditService(session),
            cache_invalidator=RedisRankingCache(
                redis_client,
                ttl_seconds=settings.ranking_cache_ttl_seconds,
            ),
        )
    finally:
        await redis_client.aclose()


RankingPublicationServiceDependency = Annotated[
    RankingPublicationService,
    Depends(get_ranking_publication_service),
]
