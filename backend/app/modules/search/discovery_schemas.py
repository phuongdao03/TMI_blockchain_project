from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.search.discovery_types import (
    RelatedWork,
    SearchAnalyticsSummary,
    TrendingSearch,
)


def _camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class DiscoverySchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class TrendingSearchData(DiscoverySchema):
    query_hash: str
    query: str
    search_count: int

    @classmethod
    def from_view(cls, value: TrendingSearch) -> "TrendingSearchData":
        return cls.model_validate(value)


class RelatedWorkData(DiscoverySchema):
    id: UUID
    slug: str
    title: str
    short_description: str
    category_name: str
    category_slug: str
    published_at: datetime

    @classmethod
    def from_view(cls, value: RelatedWork) -> "RelatedWorkData":
        return cls.model_validate(value)


class SearchClickRequest(DiscoverySchema):
    request_id: str = Field(min_length=1, max_length=128)
    work_id: UUID


class SearchClickData(DiscoverySchema):
    recorded: bool


class SearchSuppressionRequest(DiscoverySchema):
    suppressed: bool
    reason: str = Field(min_length=3, max_length=255)


class SearchSuppressionData(DiscoverySchema):
    query_hash: str
    suppressed: bool


class SearchAnalyticsPointData(DiscoverySchema):
    period_start: datetime
    category_slug: str | None
    search_count: int
    zero_result_count: int
    click_count: int
    latency_p95_ms: int


class SearchAnalyticsData(DiscoverySchema):
    search_count: int
    zero_result_count: int
    click_count: int
    click_through_rate: float
    zero_result_rate: float
    latency_p95_ms: int
    points: list[SearchAnalyticsPointData]
    privacy_mode: Literal["aggregate-only"] = "aggregate-only"

    @classmethod
    def from_summary(cls, value: SearchAnalyticsSummary) -> "SearchAnalyticsData":
        return cls(
            search_count=value.search_count,
            zero_result_count=value.zero_result_count,
            click_count=value.click_count,
            click_through_rate=value.click_count / value.search_count
            if value.search_count
            else 0,
            zero_result_rate=value.zero_result_count / value.search_count
            if value.search_count
            else 0,
            latency_p95_ms=value.latency_p95_ms,
            points=[
                SearchAnalyticsPointData.model_validate(point) for point in value.points
            ],
        )
