from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PublicRankingSnapshotView:
    id: UUID
    campaign_id: UUID
    version: int
    formula_version: str
    campaign_rule_version: int
    source_digest: str
    result_digest: str
    candidate_count: int
    total_valid_votes: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PublicRankingItemView:
    work_id: UUID
    slug: str
    title: str
    short_description: str
    author_display_name: str | None
    category_id: UUID
    category_name: str
    category_slug: str | None
    rank: int
    category_rank: int
    display_order: int
    score: int
    effective_vote_count: int


@dataclass(frozen=True, slots=True)
class PublicRankingPage:
    snapshot: PublicRankingSnapshotView
    items: tuple[PublicRankingItemView, ...]
    page: int
    page_size: int
    total: int
