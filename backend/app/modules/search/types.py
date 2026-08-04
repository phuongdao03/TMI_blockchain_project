from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.modules.blockchain.models import CertificateStatus


class SearchSort(StrEnum):
    RELEVANCE = "relevance"
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_VIEWED = "most_viewed"


class TagMatchMode(StrEnum):
    ANY = "any"
    ALL = "all"


class AutocompleteKind(StrEnum):
    WORK = "work"
    CATEGORY = "category"
    TAG = "tag"


@dataclass(frozen=True, slots=True)
class AutocompleteSuggestion:
    kind: AutocompleteKind
    label: str
    slug: str


@dataclass(frozen=True, slots=True)
class SearchFilters:
    category_slug: str | None = None
    tag_slugs: tuple[str, ...] = ()
    tag_match: TagMatchMode = TagMatchMode.ANY
    organization_code: str | None = None
    published_from: datetime | None = None
    published_to: datetime | None = None
    has_blockchain_proof: bool | None = None
    certificate_status: CertificateStatus | None = None


@dataclass(frozen=True, slots=True)
class SearchWorkProjection:
    id: UUID
    slug: str
    title: str
    short_description: str
    author_display_name: str | None
    category_name: str
    category_slug: str
    certificate_number: str | None
    certificate_status: CertificateStatus | None
    published_at: datetime


@dataclass(frozen=True, slots=True)
class SearchCursor:
    exact_match: int
    relevance: Decimal
    published_at: datetime
    work_id: UUID
    sort: SearchSort = SearchSort.RELEVANCE
    view_count: int = 0


@dataclass(frozen=True, slots=True)
class SearchPage:
    items: tuple[SearchWorkProjection, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class SearchResult:
    page: SearchPage
    duration_ms: int
    version: str = "search-v1"


@dataclass(frozen=True, slots=True)
class SearchFacetValue:
    slug: str
    label: str
    count: int


@dataclass(frozen=True, slots=True)
class SearchFacets:
    categories: tuple[SearchFacetValue, ...]
    tags: tuple[SearchFacetValue, ...]
    approximate: bool = False
