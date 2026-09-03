from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.search.dependencies import enforce_public_search_rate_limit
from app.modules.search.discovery_dependencies import get_search_discovery_service
from app.modules.search.discovery_models import SearchSnapshotPeriod
from app.modules.search.discovery_types import RelatedWork, TrendingSearch


class DiscoveryStub:
    async def trending(
        self, *, period: SearchSnapshotPeriod, limit: int
    ) -> tuple[TrendingSearch, ...]:
        assert period is SearchSnapshotPeriod.DAILY
        assert limit == 5
        return (TrendingSearch("a" * 64, "sơn mài", 9),)

    async def related(self, *, slug: str, limit: int) -> tuple[RelatedWork, ...]:
        assert slug == "tac-pham-goc"
        assert limit == 6
        return (
            RelatedWork(
                uuid4(),
                "tac-pham-lien-quan",
                "Tác phẩm liên quan",
                "Mô tả công khai",
                "Mỹ thuật",
                "my-thuat",
                datetime(2026, 8, 1, tzinfo=UTC),
            ),
        )

    async def record_click(self, *, request_id: str, work_id: object) -> bool:
        return request_id == "search-request" and work_id is not None


def _client() -> TestClient:
    app = create_application()
    app.dependency_overrides[get_search_discovery_service] = lambda: DiscoveryStub()
    app.dependency_overrides[enforce_public_search_rate_limit] = lambda: None
    return TestClient(app)


def test_public_trending_and_related_contracts_are_privacy_allowlists() -> None:
    with _client() as client:
        trending = client.get("/api/v1/public/discovery/trending", params={"limit": 5})
        related = client.get("/api/v1/public/works/tac-pham-goc/related")

    assert trending.status_code == 200
    assert set(trending.json()["data"][0]) == {
        "queryHash",
        "query",
        "searchCount",
    }
    assert related.status_code == 200
    assert set(related.json()["data"][0]) == {
        "id",
        "slug",
        "title",
        "shortDescription",
        "categoryName",
        "categorySlug",
        "publishedAt",
    }
    assert "ownerUserId" not in related.text
    assert "dossierId" not in related.text


def test_public_click_contract_is_idempotent_shaped_and_validated() -> None:
    work_id = str(uuid4())
    with _client() as client:
        response = client.post(
            "/api/v1/public/search/clicks",
            json={"requestId": "search-request", "workId": work_id},
        )
        invalid = client.post(
            "/api/v1/public/search/clicks",
            json={"requestId": "", "workId": "not-a-uuid"},
        )

    assert response.status_code == 200
    assert response.json()["data"] == {"recorded": True}
    assert invalid.status_code == 422
