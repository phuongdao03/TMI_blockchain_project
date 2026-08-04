from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TrendingSearch:
    query_hash: str
    query: str
    search_count: int


@dataclass(frozen=True, slots=True)
class RelatedWork:
    id: UUID
    slug: str
    title: str
    short_description: str
    category_name: str
    category_slug: str
    published_at: datetime


@dataclass(frozen=True, slots=True)
class SearchAnalyticsPoint:
    period_start: datetime
    category_slug: str | None
    search_count: int
    zero_result_count: int
    click_count: int
    latency_p95_ms: int


@dataclass(frozen=True, slots=True)
class SearchAnalyticsSummary:
    search_count: int
    zero_result_count: int
    click_count: int
    latency_p95_ms: int
    points: tuple[SearchAnalyticsPoint, ...]
