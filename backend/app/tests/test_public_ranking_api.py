from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.public.dependencies import enforce_public_rate_limit
from app.modules.ranking.public_dependencies import get_public_ranking_service
from app.modules.ranking.public_types import (
    PublicRankingItemView,
    PublicRankingPage,
    PublicRankingSnapshotView,
)

CAMPAIGN_ID = UUID("30000000-0000-0000-0000-000000000001")
SNAPSHOT_ID = UUID("30000000-0000-0000-0000-000000000002")
WORK_ID = UUID("40000000-0000-0000-0000-000000000001")
CATEGORY_ID = UUID("50000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def _page() -> PublicRankingPage:
    return PublicRankingPage(
        snapshot=PublicRankingSnapshotView(
            id=SNAPSHOT_ID,
            campaign_id=CAMPAIGN_ID,
            version=2,
            formula_version="effective-votes-v1",
            campaign_rule_version=4,
            source_digest="a" * 64,
            result_digest="b" * 64,
            candidate_count=1,
            total_valid_votes=3,
            created_at=NOW,
        ),
        items=(
            PublicRankingItemView(
                work_id=WORK_ID,
                slug="heritage-work",
                title="Heritage work",
                short_description="A public ranked work.",
                author_display_name="Public author",
                category_id=CATEGORY_ID,
                category_name="Heritage",
                category_slug="heritage",
                rank=1,
                category_rank=1,
                display_order=1,
                score=3,
                effective_vote_count=3,
            ),
        ),
        page=1,
        page_size=20,
        total=1,
    )


class FakePublicRankingService:
    async def get_ranking(self, **kwargs: object) -> PublicRankingPage:
        assert kwargs == {
            "campaign_slug": "heritage-campaign",
            "version": 2,
            "category_id": CATEGORY_ID,
            "page": 1,
            "page_size": 20,
        }
        return _page()


def _client() -> TestClient:
    app = create_application()
    app.dependency_overrides[get_public_ranking_service] = FakePublicRankingService
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    return TestClient(app)


def test_public_ranking_contract_is_allowlisted_and_versioned() -> None:
    with _client() as client:
        response = client.get(
            "/api/v1/public/campaigns/heritage-campaign/ranking",
            params={"version": 2, "categoryId": str(CATEGORY_ID)},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["snapshot"]["version"] == 2
    assert payload["data"]["items"][0]["displayOrder"] == 1
    assert payload["data"]["pagination"] == {"page": 1, "pageSize": 20, "total": 1}
    assert "ownerUserId" not in response.text
    assert "dossierId" not in response.text


def test_public_ranking_rejects_invalid_pagination_before_service() -> None:
    app = create_application()
    called = False

    class Service:
        async def get_ranking(self, **kwargs: object) -> PublicRankingPage:
            nonlocal called
            called = True
            return _page()

    app.dependency_overrides[get_public_ranking_service] = Service
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/public/campaigns/heritage-campaign/ranking",
            params={"pageSize": 0},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert called is False
