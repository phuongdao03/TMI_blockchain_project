import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.modules.ranking.public_service import PublicRankingService
from app.modules.ranking.public_types import (
    PublicRankingItemView,
    PublicRankingPage,
    PublicRankingSnapshotView,
)
from app.modules.ranking.ranking_cache import (
    GENERATION_KEY,
    RedisRankingCache,
    public_ranking_cache_key,
)


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


def _page() -> PublicRankingPage:
    snapshot = PublicRankingSnapshotView(
        id=UUID("60000000-0000-0000-0000-000000000001"),
        campaign_id=UUID("30000000-0000-0000-0000-000000000001"),
        version=3,
        formula_version="v1",
        campaign_rule_version=1,
        source_digest="source",
        result_digest="result",
        candidate_count=1,
        total_valid_votes=2,
        created_at=datetime(2026, 8, 3, 8, tzinfo=UTC),
    )
    item = PublicRankingItemView(
        work_id=UUID("70000000-0000-0000-0000-000000000001"),
        slug="work-one",
        title="Work One",
        short_description="Short",
        author_display_name="Author",
        category_id=UUID("80000000-0000-0000-0000-000000000001"),
        category_name="Category",
        category_slug="category",
        rank=1,
        category_rank=1,
        display_order=1,
        score=10,
        effective_vote_count=2,
    )
    return PublicRankingPage(snapshot, (item,), page=1, page_size=20, total=1)


def test_ranking_cache_key_contains_all_query_dimensions() -> None:
    published = public_ranking_cache_key(
        campaign_slug=" Campaign ",
        version=None,
        category_id=None,
        page=1,
        page_size=20,
    )
    historical = public_ranking_cache_key(
        campaign_slug="campaign",
        version=2,
        category_id=UUID("80000000-0000-0000-0000-000000000001"),
        page=2,
        page_size=10,
    )
    assert published != historical
    assert published.startswith("ranking:public:")


def test_ranking_cache_uses_generation_and_fails_open_on_redis_errors() -> None:
    async def exercise() -> None:
        redis = FakeRedis()
        cache = RedisRankingCache(redis, ttl_seconds=30)  # type: ignore[arg-type]
        key = public_ranking_cache_key(
            campaign_slug="campaign",
            version=None,
            category_id=None,
            page=1,
            page_size=20,
        )
        assert await cache.get(key) is None
        await cache.set(key, '{"total": 1}')
        assert await cache.get(key) == '{"total": 1}'
        writer = RedisRankingCache(redis, ttl_seconds=30)  # type: ignore[arg-type]
        assert await writer.get(key) == '{"total": 1}'
        assert await cache.invalidate(reason="ranking.results.published") == 1
        await writer.set(key, '{"total": 2}')
        assert await cache.get(key) is None
        assert redis.values[GENERATION_KEY] == b"1"

        failing = RedisRankingCache(FailingRedis(), ttl_seconds=30)  # type: ignore[arg-type]
        assert await failing.get(key) is None
        await failing.set(key, "safe")
        assert await failing.invalidate(reason="test") is None

    asyncio.run(exercise())


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        del args


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class RecordingRepository:
    def __init__(self, page: PublicRankingPage) -> None:
        self.page = page
        self.snapshot_calls = 0
        self.item_calls = 0

    async def get_snapshot(
        self, *, campaign_slug: str, version: int | None
    ) -> PublicRankingSnapshotView:
        del campaign_slug, version
        self.snapshot_calls += 1
        return self.page.snapshot

    async def list_items(
        self, **kwargs: object
    ) -> tuple[tuple[PublicRankingItemView, ...], int]:
        del kwargs
        self.item_calls += 1
        return self.page.items, self.page.total


class RecordingCache:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key: str) -> str | None:
        del key
        self.get_calls += 1
        return self.value

    async def set(self, key: str, value: str) -> None:
        del key
        self.set_calls += 1
        self.value = value


def test_public_ranking_service_reads_and_writes_serialized_cache() -> None:
    async def exercise() -> None:
        page = _page()
        repository = RecordingRepository(page)
        cache = RecordingCache()
        service = PublicRankingService(
            FakeSession(),  # type: ignore[arg-type]
            repository,  # type: ignore[arg-type]
            cache=cache,
        )
        first = await service.get_ranking(
            campaign_slug="campaign",
            version=None,
            category_id=None,
            page=1,
            page_size=20,
        )
        second = await service.get_ranking(
            campaign_slug="campaign",
            version=None,
            category_id=None,
            page=1,
            page_size=20,
        )
        assert first == page
        assert second == page
        assert repository.snapshot_calls == 1
        assert repository.item_calls == 1
        assert cache.get_calls == 2
        assert cache.set_calls == 1

    asyncio.run(exercise())


def test_public_ranking_service_ignores_malformed_cached_payload() -> None:
    async def exercise() -> None:
        page = _page()
        repository = RecordingRepository(page)
        cache = RecordingCache("not-json")
        service = PublicRankingService(
            FakeSession(),  # type: ignore[arg-type]
            repository,  # type: ignore[arg-type]
            cache=cache,
        )
        result = await service.get_ranking(
            campaign_slug="campaign",
            version=None,
            category_id=None,
            page=1,
            page_size=20,
        )
        assert result == page
        assert repository.snapshot_calls == 1
        assert cache.set_calls == 1

    asyncio.run(exercise())
