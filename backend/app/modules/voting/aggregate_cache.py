import logging
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisVoteSummaryCache:
    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, campaign_id: UUID) -> str | None:
        try:
            value = await self._redis.get(self._key(campaign_id))
        except (RedisError, OSError, TimeoutError):
            logger.warning(
                "voting_summary_cache_unavailable",
                extra={"action": "get", "campaign_id": str(campaign_id)},
            )
            return None
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    async def set(self, campaign_id: UUID, payload: str) -> None:
        try:
            await self._redis.set(self._key(campaign_id), payload, ex=self._ttl_seconds)
        except (RedisError, OSError, TimeoutError):
            logger.warning(
                "voting_summary_cache_unavailable",
                extra={"action": "set", "campaign_id": str(campaign_id)},
            )

    async def invalidate(self, campaign_id: UUID) -> None:
        try:
            await self._redis.delete(self._key(campaign_id))
        except (RedisError, OSError, TimeoutError):
            logger.warning(
                "voting_summary_cache_unavailable",
                extra={"action": "invalidate", "campaign_id": str(campaign_id)},
            )

    @staticmethod
    def _key(campaign_id: UUID) -> str:
        return f"voting:v1:campaign:{campaign_id}:summary"
