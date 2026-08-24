import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.search.discovery_models import SearchEvent, SearchSnapshotPeriod
from app.modules.search.discovery_service import SearchDiscoveryService
from app.modules.search.discovery_types import (
    RelatedWork,
    SearchAnalyticsSummary,
    TrendingSearch,
)
from app.modules.search.privacy import is_safe_aggregate_query
from app.modules.search.service import PublicSearchService, SearchRepositoryPort
from app.modules.search.types import SearchPage, SearchWorkProjection


class RecordingRepository:
    def __init__(self) -> None:
        self.events: list[SearchEvent] = []
        self.aggregate_calls: list[dict[str, object]] = []
        self.commits = 0

    async def add_event(self, event: SearchEvent) -> bool:
        self.events.append(event)
        return True

    async def commit(self) -> None:
        self.commits += 1

    async def record_click(self, request_id: str, work_id: UUID) -> bool:
        return request_id == "request-1" and work_id.int > 0

    async def aggregate(self, **kwargs: object) -> int:
        self.aggregate_calls.append(kwargs)
        return 3

    async def trending(self, *, period: str, limit: int) -> tuple[TrendingSearch, ...]:
        del period, limit
        return (TrendingSearch("a" * 64, "sÆ¡n mÃ i", 12),)

    async def related(
        self, *, slug: str, limit: int, now: datetime
    ) -> tuple[RelatedWork, ...]:
        del slug, limit, now
        return (
            RelatedWork(
                uuid4(),
                "tac-pham-lien-quan",
                "TÃ¡c pháº©m liÃªn quan",
                "MÃ´ táº£ cÃ´ng khai",
                "Má»¹ thuáº­t",
                "my-thuat",
                datetime(2026, 8, 1, tzinfo=UTC),
            ),
        )

    async def analytics(self, **kwargs: object) -> SearchAnalyticsSummary:
        del kwargs
        return SearchAnalyticsSummary(10, 2, 4, 120, ())

    async def suppress(self, **kwargs: object) -> None:
        del kwargs


class MemoryCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value

    async def reserve(self, key: str, *, seconds: int = 3) -> bool:
        del key, seconds
        return True

    async def release(self, key: str) -> None:
        del key


class StampedeCache(MemoryCache):
    def __init__(self) -> None:
        super().__init__()
        self.locked = False

    async def reserve(self, key: str, *, seconds: int = 3) -> bool:
        del key, seconds
        if self.locked:
            return False
        self.locked = True
        return True

    async def release(self, key: str) -> None:
        del key
        self.locked = False


class ResultRepository:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, query: object, **kwargs: object) -> SearchPage:
        del query, kwargs
        self.calls += 1
        await asyncio.sleep(0.03)
        return SearchPage(
            (
                SearchWorkProjection(
                    uuid4(),
                    "son-mai",
                    "SÆ¡n mÃ i",
                    "MÃ´ táº£",
                    None,
                    "Má»¹ thuáº­t",
                    "my-thuat",
                    None,
                    None,
                    datetime(2026, 8, 1, tzinfo=UTC),
                ),
            ),
            None,
        )

    async def facets(self, query: object, **kwargs: object) -> object:
        raise AssertionError("not used")

    async def autocomplete(self, query: object, **kwargs: object) -> object:
        raise AssertionError("not used")


def _principal(*roles: str) -> AuthPrincipal:
    return AuthPrincipal(uuid4(), uuid4(), "admin@example.test", roles)


def test_search_events_are_hashed_and_pii_is_never_available_to_aggregation() -> None:
    async def scenario() -> None:
        repository = RecordingRepository()
        service = SearchDiscoveryService(repository)  # type: ignore[arg-type]
        await service.record_search(
            request_id="request-1",
            normalized_query="user@example.test",
            category_slug=None,
            result_count=0,
            duration_ms=14,
        )
        event = repository.events[0]
        assert event.normalized_query is None
        assert event.query_hash != "user@example.test"
        assert len(event.query_hash) == 64
        assert repository.commits == 1

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "query",
    ["0901234567", "https://example.test/private", "A" * 24, "a@b.test"],
)
def test_privacy_policy_rejects_sensitive_and_high_entropy_queries(query: str) -> None:
    assert is_safe_aggregate_query(query) is False


def test_snapshot_window_is_closed_and_materialization_is_repeatable() -> None:
    async def scenario() -> None:
        repository = RecordingRepository()
        service = SearchDiscoveryService(repository, minimum_trending_count=7)  # type: ignore[arg-type]
        now = datetime(2026, 8, 1, 12, 34, tzinfo=UTC)
        first_count = await service.materialize(
            period=SearchSnapshotPeriod.HOURLY, now=now
        )
        second_count = await service.materialize(
            period=SearchSnapshotPeriod.HOURLY, now=now
        )
        assert (first_count, second_count) == (3, 3)
        first = repository.aggregate_calls[0]
        assert first["start"] == datetime(2026, 8, 1, 11, tzinfo=UTC)
        assert first["end"] == datetime(2026, 8, 1, 12, tzinfo=UTC)
        assert first["minimum_count"] == 7
        assert repository.aggregate_calls[0] == repository.aggregate_calls[1]

    asyncio.run(scenario())


def test_trending_and_related_are_deterministic_cache_namespaces() -> None:
    async def scenario() -> None:
        repository = RecordingRepository()
        cache = MemoryCache()
        service = SearchDiscoveryService(repository, cache=cache)  # type: ignore[arg-type]
        assert (await service.trending())[0].query == "sÆ¡n mÃ i"
        first = await service.related(slug="son-mai")
        second = await service.related(slug="son-mai")
        assert first == second
        assert any(key.startswith("trending:") for key in cache.values)
        assert any(key.startswith("related:") for key in cache.values)

    asyncio.run(scenario())


def test_analytics_is_server_authorized_and_period_bounded() -> None:
    async def scenario() -> None:
        repository = RecordingRepository()
        service = SearchDiscoveryService(repository)  # type: ignore[arg-type]
        start = datetime(2026, 8, 1, tzinfo=UTC)
        end = start + timedelta(days=1)
        summary = await service.analytics(
            _principal("SUPER_ADMIN"), start=start, end=end
        )
        assert summary.search_count == 10
        with pytest.raises(DomainError) as forbidden:
            await service.analytics(_principal("VIEWER"), start=start, end=end)
        assert forbidden.value.code == "SEARCH_ANALYTICS_FORBIDDEN"
        with pytest.raises(DomainError) as invalid:
            await service.analytics(_principal("SUPER_ADMIN"), start=end, end=start)
        assert invalid.value.code == "SEARCH_PERIOD_INVALID"

    asyncio.run(scenario())


def test_result_cache_canonicalizes_parameters_and_prevents_stampede() -> None:
    async def scenario() -> None:
        repository = ResultRepository()
        cache = StampedeCache()
        typed_repository = cast(SearchRepositoryPort, repository)
        first = PublicSearchService(typed_repository, result_cache=cache)
        second = PublicSearchService(typed_repository, result_cache=cache)
        results = await asyncio.gather(
            first.search(query="SÆ¡n mÃ i", category="my-thuat"),
            second.search(query="SÆ¡n mÃ i", category="my-thuat"),
        )
        assert repository.calls == 1
        assert results[0].page == results[1].page
        assert len(cache.values) == 1
        assert next(iter(cache.values)).startswith("result:")

    asyncio.run(scenario())
