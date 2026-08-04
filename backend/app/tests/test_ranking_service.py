import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.errors import DomainError
from app.modules.ranking.formula import RankingCandidate
from app.modules.ranking.service import RankingService
from app.modules.ranking.types import RankingCampaignSource
from app.modules.voting.models import CampaignStatus

CAMPAIGN_ID = UUID("10000000-0000-0000-0000-000000000001")
WORK_A = UUID("20000000-0000-0000-0000-000000000001")
WORK_B = UUID("20000000-0000-0000-0000-000000000002")
CATEGORY_ID = UUID("20000000-0000-0000-0001-000000000001")
NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


class FakeRankingRepository:
    def __init__(
        self,
        campaign: RankingCampaignSource | None,
        candidates: tuple[RankingCandidate, ...] = (),
    ) -> None:
        self.campaign = campaign
        self.candidates = candidates

    async def get_campaign(self, campaign_id: UUID) -> RankingCampaignSource | None:
        assert campaign_id == CAMPAIGN_ID
        return self.campaign

    async def list_candidates(self, campaign_id: UUID) -> tuple[RankingCandidate, ...]:
        assert campaign_id == CAMPAIGN_ID
        return self.candidates


def _campaign(status: CampaignStatus) -> RankingCampaignSource:
    return RankingCampaignSource(
        campaign_id=CAMPAIGN_ID,
        status=status,
        rule_version=3,
        end_at=NOW,
    )


def test_ranking_service_calculates_closed_campaign() -> None:
    repository = FakeRankingRepository(
        _campaign(CampaignStatus.ENDED),
        (
            RankingCandidate(WORK_A, CATEGORY_ID, 2),
            RankingCandidate(WORK_B, CATEGORY_ID, 5),
        ),
    )

    result = asyncio.run(RankingService(repository).calculate(CAMPAIGN_ID))

    assert result.campaign == repository.campaign
    assert [item.work_id for item in result.calculation.items] == [WORK_B, WORK_A]


def test_ranking_service_rejects_missing_campaign() -> None:
    with pytest.raises(DomainError) as captured:
        asyncio.run(RankingService(FakeRankingRepository(None)).calculate(CAMPAIGN_ID))

    assert captured.value.code == "RANKING_CAMPAIGN_NOT_FOUND"
    assert captured.value.status_code == 404


def test_ranking_service_rejects_campaign_that_is_not_closed() -> None:
    with pytest.raises(DomainError) as captured:
        asyncio.run(
            RankingService(
                FakeRankingRepository(_campaign(CampaignStatus.ACTIVE))
            ).calculate(CAMPAIGN_ID)
        )

    assert captured.value.code == "RANKING_CAMPAIGN_NOT_CLOSED"
    assert captured.value.status_code == 409


def test_ranking_service_rejects_campaign_without_approved_candidates() -> None:
    with pytest.raises(DomainError) as captured:
        asyncio.run(
            RankingService(
                FakeRankingRepository(_campaign(CampaignStatus.RESULT_PENDING))
            ).calculate(CAMPAIGN_ID)
        )

    assert captured.value.code == "RANKING_CANDIDATES_EMPTY"
    assert captured.value.status_code == 409
