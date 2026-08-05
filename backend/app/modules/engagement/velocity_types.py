from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EngagementVelocityDaily:
    work_id: UUID
    category_id: UUID
    metric_date: date
    views: int
    shares: int
    qr_scans: int
    favorites: int


@dataclass(frozen=True, slots=True)
class EngagementVelocityItem:
    work_id: UUID
    category_id: UUID
    score: Decimal
    rank: int
    display_order: int


@dataclass(frozen=True, slots=True)
class EngagementVelocityCalculation:
    formula_version: str
    items: tuple[EngagementVelocityItem, ...]
    total_score: Decimal


@dataclass(frozen=True, slots=True)
class EngagementVelocitySnapshotDraft:
    id: UUID
    window_start: date
    window_end: date
    formula_version: str
    candidate_count: int
    total_score: Decimal
    generated_at: datetime
    items: tuple[EngagementVelocityItem, ...]


@dataclass(frozen=True, slots=True)
class EngagementVelocitySnapshotView:
    id: UUID
    window_start: date
    window_end: date
    formula_version: str
    generated_at: datetime
    items: tuple[EngagementVelocityItem, ...]
