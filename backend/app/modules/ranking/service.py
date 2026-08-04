from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from app.core.errors import DomainError
from app.modules.ranking.formula import (
    RankingCandidate,
    calculate_rankings,
)
from app.modules.ranking.types import (
    CLOSED_RANKING_CAMPAIGN_STATUSES,
    RankingCampaignSource,
    RankingRun,
)
from app.modules.voting.models import PeriodType


class RankingRepositoryPort(Protocol):
    async def get_campaign(self, campaign_id: UUID) -> RankingCampaignSource | None: ...

    async def list_candidates(
        self, campaign_id: UUID
    ) -> tuple[RankingCandidate, ...]: ...


class PeriodicRankingRepositoryPort(Protocol):
    async def list_pending_periodic_campaign_ids(
        self, *, period_type: PeriodType, limit: int
    ) -> tuple[UUID, ...]: ...


class PeriodicRankingService:
    def __init__(
        self,
        repository: PeriodicRankingRepositoryPort,
        *,
        period_type: PeriodType,
        enqueue: Callable[[UUID], None],
    ) -> None:
        self._repository = repository
        self._period_type = period_type
        self._enqueue = enqueue

    async def reconcile(self, *, limit: int = 100) -> int:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        campaign_ids = await self._repository.list_pending_periodic_campaign_ids(
            period_type=self._period_type,
            limit=limit,
        )
        for campaign_id in campaign_ids:
            self._enqueue(campaign_id)
        return len(campaign_ids)


class MonthlyRankingService(PeriodicRankingService):
    def __init__(
        self,
        repository: PeriodicRankingRepositoryPort,
        *,
        enqueue: Callable[[UUID], None],
    ) -> None:
        super().__init__(
            repository,
            period_type=PeriodType.MONTHLY,
            enqueue=enqueue,
        )


class QuarterlyRankingService(PeriodicRankingService):
    def __init__(
        self,
        repository: PeriodicRankingRepositoryPort,
        *,
        enqueue: Callable[[UUID], None],
    ) -> None:
        super().__init__(
            repository,
            period_type=PeriodType.QUARTERLY,
            enqueue=enqueue,
        )


class YearlyRankingService(PeriodicRankingService):
    def __init__(
        self,
        repository: PeriodicRankingRepositoryPort,
        *,
        enqueue: Callable[[UUID], None],
    ) -> None:
        super().__init__(
            repository,
            period_type=PeriodType.YEARLY,
            enqueue=enqueue,
        )


class RankingService:
    def __init__(self, repository: RankingRepositoryPort) -> None:
        self._repository = repository

    async def calculate(self, campaign_id: UUID) -> RankingRun:
        campaign = await self._repository.get_campaign(campaign_id)
        if campaign is None:
            raise DomainError(
                code="RANKING_CAMPAIGN_NOT_FOUND",
                message="Ranking campaign was not found.",
                status_code=404,
            )
        if campaign.status not in CLOSED_RANKING_CAMPAIGN_STATUSES:
            raise DomainError(
                code="RANKING_CAMPAIGN_NOT_CLOSED",
                message="Ranking can only be calculated for a closed campaign.",
                status_code=409,
            )
        candidates = await self._repository.list_candidates(campaign_id)
        if not candidates:
            raise DomainError(
                code="RANKING_CANDIDATES_EMPTY",
                message="Ranking campaign has no approved candidates.",
                status_code=409,
            )
        return RankingRun(
            campaign=campaign,
            calculation=calculate_rankings(candidates),
        )
