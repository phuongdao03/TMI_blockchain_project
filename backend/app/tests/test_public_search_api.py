import asyncio
from datetime import UTC, datetime
from typing import cast
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from starlette.requests import Request

from app.core.config import Settings
from app.main import create_application
from app.modules.blockchain.models import CertificateStatus
from app.modules.search.dependencies import (
    enforce_public_search_rate_limit,
    get_public_search_service,
)
from app.modules.search.errors import SearchRateLimitedError
from app.modules.search.service import PublicSearchService
from app.modules.search.types import (
    AutocompleteKind,
    AutocompleteSuggestion,
    SearchFacets,
    SearchFacetValue,
    SearchPage,
    SearchWorkProjection,
)


class RecordingSearchRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def search(self, query: object, **kwargs: object) -> SearchPage:
        self.calls.append({"query": query, **kwargs})
        return SearchPage(
            items=(
                SearchWorkProjection(
                    id=uuid4(),
                    slug="heritage-lacquer",
                    title="Sơn mài di sản",
                    short_description="Hồ sơ công khai đã được xác lập.",
                    author_display_name="Nguyễn An",
                    category_name="Mỹ thuật",
                    category_slug="my-thuat",
                    certificate_number="TMI-2026-001",
                    certificate_status=CertificateStatus.ACTIVE,
                    published_at=datetime(2026, 8, 1, tzinfo=UTC),
                ),
            ),
            next_cursor="next-page",
        )

    async def facets(self, query: object, **kwargs: object) -> SearchFacets:
        self.calls.append({"query": query, **kwargs})
        return SearchFacets(
            categories=(SearchFacetValue(slug="my-thuat", label="Mỹ thuật", count=7),),
            tags=(SearchFacetValue(slug="di-san", label="Di sản", count=4),),
        )

    async def autocomplete(
        self,
        query: object,
        **kwargs: object,
    ) -> tuple[AutocompleteSuggestion, ...]:
        self.calls.append({"query": query, **kwargs})
        return (
            AutocompleteSuggestion(
                kind=AutocompleteKind.WORK,
                label="Sơn mài di sản",
                slug="son-mai-di-san",
            ),
            AutocompleteSuggestion(
                kind=AutocompleteKind.CATEGORY,
                label="Sơn mài",
                slug="son-mai",
            ),
        )


class BlockingRedis:
    def __init__(self) -> None:
        self.keys: list[str] = []

    async def eval(
        self,
        script: str,
        key_count: int,
        key: str,
        window: int,
    ) -> list[int]:
        del script, key_count, window
        self.keys.append(key)
        return [2, 31]

    async def aclose(self) -> None:
        return None


def _client(repository: RecordingSearchRepository) -> TestClient:
    app = create_application()
    app.dependency_overrides[get_public_search_service] = lambda: PublicSearchService(
        repository
    )
    app.dependency_overrides[enforce_public_search_rate_limit] = lambda: None
    return TestClient(app)


def test_public_search_contract_is_allowlisted_and_reports_safe_metadata() -> None:
    repository = RecordingSearchRepository()
    with _client(repository) as client:
        response = client.get(
            "/api/v1/public/search",
            params={
                "q": "  Sơn   mài ",
                "category": "my-thuat",
                "tags": "di-san,son-mai",
                "sort": "relevance",
                "pageSize": 10,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert set(payload["data"][0]) == {
        "id",
        "slug",
        "title",
        "shortDescription",
        "authorDisplayName",
        "categoryName",
        "categorySlug",
        "certificateNumber",
        "certificateStatus",
        "publishedAt",
    }
    assert set(payload["meta"]) == {
        "requestId",
        "nextCursor",
        "durationMs",
        "version",
    }
    assert payload["meta"]["version"] == "search-v1"
    assert "ownerUserId" not in response.text
    assert "dossierId" not in response.text
    assert len(repository.calls) == 1


def test_public_search_rejects_unknown_sort_and_filter_with_stable_codes() -> None:
    repository = RecordingSearchRepository()
    with _client(repository) as client:
        bad_sort = client.get(
            "/api/v1/public/search", params={"q": "di sản", "sort": "votes"}
        )
        bad_filter = client.get(
            "/api/v1/public/search", params={"q": "di sản", "private": "true"}
        )

    assert bad_sort.status_code == 422
    assert bad_sort.json()["error"]["code"] == "SEARCH_SORT_INVALID"
    assert bad_filter.status_code == 422
    assert bad_filter.json()["error"]["code"] == "SEARCH_FILTER_INVALID"
    assert repository.calls == []


def test_public_search_validates_empty_relevance_and_date_range() -> None:
    repository = RecordingSearchRepository()
    with _client(repository) as client:
        empty_relevance = client.get(
            "/api/v1/public/search", params={"sort": "relevance"}
        )
        reversed_dates = client.get(
            "/api/v1/public/search",
            params={
                "q": "di sản",
                "publishedFrom": "2026-08-02T00:00:00Z",
                "publishedTo": "2026-08-01T00:00:00Z",
            },
        )

    assert empty_relevance.status_code == 422
    assert empty_relevance.json()["error"]["code"] == "SEARCH_SORT_INVALID"
    assert reversed_dates.status_code == 422
    assert reversed_dates.json()["error"]["code"] == "SEARCH_FILTER_INVALID"
    assert repository.calls == []


def test_public_search_rate_limit_has_scoped_key_and_stable_error() -> None:
    async def scenario() -> None:
        redis = BlockingRedis()
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/public/search",
                "headers": [],
                "client": ("203.0.113.9", 443),
            }
        )
        settings = Settings(search_rate_limit=1, search_rate_window_seconds=60)
        with patch(
            "app.modules.search.dependencies.Redis.from_url",
            return_value=cast(Redis, redis),
        ):
            with pytest.raises(SearchRateLimitedError) as captured:
                await enforce_public_search_rate_limit(request, settings)
        assert captured.value.code == "SEARCH_RATE_LIMITED"
        assert captured.value.details == {"retryAfterSeconds": 31}
        assert redis.keys[0].startswith("public:search:ip:")
        assert "203.0.113.9" not in redis.keys[0]

    asyncio.run(scenario())


def test_public_search_facets_contract_uses_the_same_filter_allowlist() -> None:
    repository = RecordingSearchRepository()
    with _client(repository) as client:
        response = client.get(
            "/api/v1/public/search/facets",
            params={
                "q": "sơn mài",
                "category": "my-thuat",
                "tags": "di-san,son-mai",
                "tagsMode": "all",
            },
        )
        rejected = client.get(
            "/api/v1/public/search/facets",
            params={"q": "sơn mài", "ownerId": "private-owner"},
        )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "categories": [{"slug": "my-thuat", "label": "Mỹ thuật", "count": 7}],
        "tags": [{"slug": "di-san", "label": "Di sản", "count": 4}],
        "approximate": False,
    }
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "SEARCH_FILTER_INVALID"


def test_public_autocomplete_contract_rejects_short_and_unknown_queries() -> None:
    repository = RecordingSearchRepository()
    with _client(repository) as client:
        response = client.get(
            "/api/v1/public/search/autocomplete",
            params={"q": "  Sơn   mài "},
        )
        too_short = client.get(
            "/api/v1/public/search/autocomplete",
            params={"q": "s"},
        )
        unknown = client.get(
            "/api/v1/public/search/autocomplete",
            params={"q": "sơn", "private": "true"},
        )

    assert response.status_code == 200
    assert response.json()["data"] == [
        {"kind": "work", "label": "Sơn mài di sản", "slug": "son-mai-di-san"},
        {"kind": "category", "label": "Sơn mài", "slug": "son-mai"},
    ]
    assert too_short.status_code == 422
    assert too_short.json()["error"]["code"] == "SEARCH_QUERY_INVALID"
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "SEARCH_FILTER_INVALID"
    assert len(repository.calls) == 1
