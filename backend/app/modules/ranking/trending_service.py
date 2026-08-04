from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.modules.ranking.trending_formula import (
    TrendingCandidate,
    calculate_trending,
)
from app.modules.ranking.trending_types import TrendingRun, TrendingWindow


def floor_to_hour(value: datetime) -> datetime:
    normalized = (
        value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    )
    return normalized.replace(minute=0, second=0, microsecond=0)


class TrendingRepositoryPort(Protocol):
    async def list_candidates(
        self, *, window: TrendingWindow
    ) -> tuple[TrendingCandidate, ...]: ...


class TrendingCalculator:
    def __init__(self, repository: TrendingRepositoryPort) -> None:
        self._repository = repository

    async def calculate(self, *, window_end: datetime) -> TrendingRun:
        normalized_end = floor_to_hour(window_end)
        window = TrendingWindow(
            window_start=normalized_end - timedelta(days=7),
            window_end=normalized_end,
        )
        candidates = await self._repository.list_candidates(window=window)
        return TrendingRun(window=window, calculation=calculate_trending(candidates))
