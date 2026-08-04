from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.ranking.trending_formula import TrendingCalculation


@dataclass(frozen=True, slots=True)
class TrendingWindow:
    window_start: datetime
    window_end: datetime


@dataclass(frozen=True, slots=True)
class TrendingRun:
    window: TrendingWindow
    calculation: TrendingCalculation


@dataclass(frozen=True, slots=True)
class TrendingSnapshotItemDraft:
    work_id: UUID
    category_id: UUID
    rank: int
    display_order: int
    score: int


@dataclass(frozen=True, slots=True)
class TrendingSnapshotDraft:
    id: UUID
    window_start: datetime
    window_end: datetime
    formula_version: str
    source_digest: str
    result_digest: str
    candidate_count: int
    total_score: int
    created_at: datetime
    items: tuple[TrendingSnapshotItemDraft, ...]
