from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_application
from app.modules.public.dependencies import enforce_public_rate_limit
from app.modules.ranking.formula import RankingCandidate, calculate_rankings
from app.modules.ranking.public_dependencies import get_public_ranking_service
from app.modules.ranking.public_schemas import PublicRankingData
from app.modules.ranking.public_types import (
    PublicRankingItemView,
    PublicRankingPage,
    PublicRankingSnapshotView,
)
from app.modules.ranking.ranking_cache import public_ranking_cache_key

CAMPAIGN_ID = UUID("30000000-0000-0000-0000-000000000001")
SNAPSHOT_ID = UUID("60000000-0000-0000-0000-000000000001")
WORK_ID = UUID("70000000-0000-0000-0000-000000000001")
CATEGORY_ID = UUID("80000000-0000-0000-0000-000000000001")


def _page() -> PublicRankingPage:
    return PublicRankingPage(
        snapshot=PublicRankingSnapshotView(
            id=SNAPSHOT_ID,
            campaign_id=CAMPAIGN_ID,
            version=3,
            formula_version="effective-votes-v1",
            campaign_rule_version=1,
            source_digest="a" * 64,
            result_digest="b" * 64,
            candidate_count=1,
            total_valid_votes=4,
            created_at=datetime(2026, 8, 3, 8, tzinfo=UTC),
        ),
        items=(
            PublicRankingItemView(
                work_id=WORK_ID,
                slug="public-work",
                title="Public work",
                short_description="Public ranking item.",
                author_display_name="Public author",
                category_id=CATEGORY_ID,
                category_name="Heritage",
                category_slug="heritage",
                rank=1,
                category_rank=1,
                display_order=1,
                score=4,
                effective_vote_count=4,
            ),
        ),
        page=1,
        page_size=20,
        total=1,
    )


def test_public_ranking_dto_is_an_explicit_allowlist() -> None:
    payload = PublicRankingData.from_view(_page()).model_dump(by_alias=True)

    assert set(payload) == {"snapshot", "items", "pagination"}
    assert set(payload["snapshot"]) == {
        "id",
        "campaignId",
        "version",
        "formulaVersion",
        "campaignRuleVersion",
        "sourceDigest",
        "resultDigest",
        "candidateCount",
        "totalValidVotes",
        "createdAt",
    }
    assert set(payload["items"][0]) == {
        "workId",
        "slug",
        "title",
        "shortDescription",
        "authorDisplayName",
        "categoryId",
        "categoryName",
        "categorySlug",
        "rank",
        "categoryRank",
        "displayOrder",
        "score",
        "effectiveVoteCount",
    }
    assert "ownerUserId" not in str(payload)
    assert "dossierId" not in str(payload)


def test_public_ranking_dto_rejects_unexpected_private_fields() -> None:
    payload = PublicRankingData.from_view(_page()).model_dump()
    payload["private_metadata"] = {"ownerUserId": "private"}

    with pytest.raises(ValidationError):
        PublicRankingData.model_validate(payload)


def test_public_ranking_input_limits_reject_oversized_slug_and_page() -> None:
    app = create_application()
    called = False

    class Service:
        async def get_ranking(self, **kwargs: object) -> PublicRankingPage:
            nonlocal called
            called = True
            del kwargs
            return _page()

    app.dependency_overrides[get_public_ranking_service] = Service
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    with TestClient(app) as client:
        oversized_slug = client.get(
            f"/api/v1/public/campaigns/{'x' * 181}/ranking"
        )
        oversized_page = client.get(
            "/api/v1/public/campaigns/public/ranking",
            params={"pageSize": 101},
        )

    assert oversized_slug.status_code == 422
    assert oversized_page.status_code == 422
    assert called is False


def test_public_ranking_cache_key_is_hashed_and_bounded() -> None:
    untrusted_slug = "x' OR '1'='1 " + ("a" * 10_000)
    key = public_ranking_cache_key(
        campaign_slug=untrusted_slug,
        version=3,
        category_id=CATEGORY_ID,
        page=1,
        page_size=100,
    )

    assert key.startswith("ranking:public:")
    assert len(key) == len("ranking:public:") + 64
    assert untrusted_slug not in key
    assert str(CATEGORY_ID) not in key


def test_ranking_formula_scales_and_remains_deterministic_for_large_input() -> None:
    candidates = tuple(
        RankingCandidate(
            work_id=UUID(int=index + 1),
            category_id=UUID(int=100_000 + (index % 5) + 1),
            effective_vote_count=index % 97,
        )
        for index in range(10_000)
    )

    started = perf_counter()
    result = calculate_rankings(candidates)
    elapsed = perf_counter() - started

    assert len(result.items) == 10_000
    assert result == calculate_rankings(tuple(reversed(candidates)))
    assert elapsed < 2.0
