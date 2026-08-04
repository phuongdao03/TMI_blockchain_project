from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.public.schemas import PublicSchema
from app.modules.ranking.public_types import (
    PublicRankingItemView,
    PublicRankingPage,
    PublicRankingSnapshotView,
)


class PublicRankingSnapshotData(PublicSchema):
    id: UUID
    campaign_id: UUID
    version: int
    formula_version: str
    campaign_rule_version: int
    source_digest: str = Field(min_length=64, max_length=64)
    result_digest: str = Field(min_length=64, max_length=64)
    candidate_count: int
    total_valid_votes: int
    created_at: datetime

    @classmethod
    def from_view(cls, view: PublicRankingSnapshotView) -> "PublicRankingSnapshotData":
        return cls.model_validate(view)


class PublicRankingItemData(PublicSchema):
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

    @classmethod
    def from_view(cls, view: PublicRankingItemView) -> "PublicRankingItemData":
        return cls.model_validate(view)


class PublicRankingPaginationData(PublicSchema):
    page: int
    page_size: int
    total: int


class PublicRankingData(PublicSchema):
    snapshot: PublicRankingSnapshotData
    items: list[PublicRankingItemData]
    pagination: PublicRankingPaginationData

    @classmethod
    def from_view(cls, view: PublicRankingPage) -> "PublicRankingData":
        return cls(
            snapshot=PublicRankingSnapshotData.from_view(view.snapshot),
            items=[PublicRankingItemData.from_view(item) for item in view.items],
            pagination=PublicRankingPaginationData(
                page=view.page,
                page_size=view.page_size,
                total=view.total,
            ),
        )
