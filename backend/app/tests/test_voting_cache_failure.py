import asyncio
from typing import Never, cast
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.voting.aggregate_cache import RedisVoteSummaryCache


class UnavailableRedis:
    async def get(self, _key: str) -> Never:
        raise RedisError("unavailable")

    async def set(self, *_args: object, **_kwargs: object) -> Never:
        raise RedisError("unavailable")

    async def delete(self, _key: str) -> Never:
        raise RedisError("unavailable")


def test_vote_summary_cache_fails_soft_when_redis_is_down() -> None:
    async def exercise() -> None:
        cache = RedisVoteSummaryCache(
            cast(Redis, UnavailableRedis()),
            ttl_seconds=30,
        )
        campaign_id = uuid4()
        assert await cache.get(campaign_id) is None
        await cache.set(campaign_id, "[]")
        await cache.invalidate(campaign_id)

    asyncio.run(exercise())
