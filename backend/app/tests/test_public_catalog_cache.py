import asyncio
from typing import Any

from app.modules.public.cache_events import CatalogCacheEventHandler
from app.modules.public.catalog_cache import (
    GENERATION_KEY,
    RedisPublicCatalogCache,
    public_catalog_cache_key,
    public_detail_cache_key,
    public_featured_cache_key,
    public_taxonomy_cache_key,
)
from app.modules.public.telemetry import InProcessCatalogTelemetry


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self.values.get(key)

    async def eval(
        self,
        script: str,
        number_of_keys: int,
        generation_key: str,
        value_key: str,
        expected_generation: str,
        value: str,
        ttl: str,
    ) -> int:
        del script, number_of_keys, ttl
        current = (await self.get(generation_key) or b"0").decode()
        if current != expected_generation:
            return 0
        self.values[value_key] = value.encode()
        return 1

    async def incr(self, key: str) -> int:
        current = int((await self.get(key) or b"0").decode()) + 1
        self.values[key] = str(current).encode()
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        del key, seconds
        return True


class FailingRedis(FakeRedis):
    async def get(self, key: str) -> bytes | None:
        del key
        raise OSError("redis unavailable")

    async def eval(self, *args: Any, **kwargs: Any) -> int:
        del args, kwargs
        raise OSError("redis unavailable")

    async def incr(self, key: str) -> int:
        del key
        raise OSError("redis unavailable")


class RecordingInvalidator:
    def __init__(self) -> None:
        self.reasons: list[str] = []

    async def invalidate(self, *, reason: str) -> int:
        self.reasons.append(reason)
        return len(self.reasons)


def test_versioned_keys_invalidation_stale_race_and_metrics() -> None:
    async def exercise() -> None:
        redis = FakeRedis()
        telemetry = InProcessCatalogTelemetry()
        cache = RedisPublicCatalogCache(
            redis,  # type: ignore[arg-type]
            ttl_seconds=60,
            telemetry=telemetry,
        )
        logical_key = public_catalog_cache_key({"page": 1})
        assert await cache.get(logical_key) is None

        # A publish/hide/suspend event can advance the generation while a
        # database request is still running; its old result must not be stored.
        invalidator = RedisPublicCatalogCache(
            redis,  # type: ignore[arg-type]
            ttl_seconds=60,
            telemetry=telemetry,
        )
        assert await invalidator.invalidate(reason="public_work.published") == 1
        assert await invalidator.invalidate(reason="public_work.hidden") == 2
        assert await invalidator.invalidate(reason="public_work.suspended") == 3
        await cache.set(logical_key, '{"items":[],"total":0}')
        assert not any(key.endswith(logical_key) for key in redis.values)

        current = RedisPublicCatalogCache(
            redis,  # type: ignore[arg-type]
            ttl_seconds=60,
            telemetry=telemetry,
        )
        assert await current.get(logical_key) is None
        await current.set(logical_key, '{"items":[],"total":0}')
        assert await current.get(logical_key) == '{"items":[],"total":0}'
        assert redis.values[GENERATION_KEY] == b"3"

        snapshot = telemetry.snapshot()
        assert snapshot.cache_operations["works:hit"] == 1
        assert snapshot.cache_operations["works:stale"] == 1
        assert snapshot.cache_operations["all:invalidated"] == 3
        assert snapshot.cache_hit_ratio == 1 / 3

        assert public_featured_cache_key(12) == "works:featured:12"
        assert public_detail_cache_key("A") == public_detail_cache_key("a")
        assert public_taxonomy_cache_key("tags") == "taxonomy:tags"

    asyncio.run(exercise())


def test_redis_failure_is_fail_open_and_observable() -> None:
    async def exercise() -> None:
        telemetry = InProcessCatalogTelemetry()
        cache = RedisPublicCatalogCache(
            FailingRedis(),  # type: ignore[arg-type]
            ttl_seconds=60,
            telemetry=telemetry,
        )
        assert await cache.get("works:list:any") is None
        await cache.set("works:list:any", "safe")
        assert await cache.invalidate(reason="emergency:test") is None
        snapshot = telemetry.snapshot()
        assert snapshot.cache_operations["works:error"] == 2
        assert snapshot.cache_operations["all:invalidation_error"] == 1

    asyncio.run(exercise())


def test_outbox_publish_hide_suspend_and_taxonomy_events_invalidate() -> None:
    async def exercise() -> None:
        invalidator = RecordingInvalidator()
        handler = CatalogCacheEventHandler(invalidator)
        for event_type in (
            "public_work.published",
            "public_work.hidden",
            "public_work.suspended",
        ):
            assert await handler.handle(
                aggregate_type="public_work",
                event_type=event_type,
                payload={"invalidate_cache": "true"},
            )
        assert await handler.handle(
            aggregate_type="public_category",
            event_type="public_category.updated",
            payload={"invalidate_cache": "true"},
        )
        assert not await handler.handle(
            aggregate_type="content_report",
            event_type="content_report.created",
            payload={},
        )
        assert invalidator.reasons == [
            "public_work.published",
            "public_work.hidden",
            "public_work.suspended",
            "public_category.updated",
        ]

    asyncio.run(exercise())
