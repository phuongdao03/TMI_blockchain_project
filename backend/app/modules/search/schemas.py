from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.blockchain.models import CertificateStatus
from app.modules.search.types import (
    AutocompleteKind,
    AutocompleteSuggestion,
    SearchFacets,
    SearchFacetValue,
    SearchWorkProjection,
)


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class SearchSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class SearchWorkData(SearchSchema):
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

    @classmethod
    def from_projection(cls, item: SearchWorkProjection) -> "SearchWorkData":
        return cls.model_validate(item)


class AutocompleteSuggestionData(SearchSchema):
    kind: AutocompleteKind
    label: str
    slug: str

    @classmethod
    def from_projection(
        cls,
        item: AutocompleteSuggestion,
    ) -> "AutocompleteSuggestionData":
        return cls.model_validate(item)


class SearchResponseMeta(SearchSchema):
    request_id: str
    next_cursor: str | None
    duration_ms: int = Field(ge=0)
    version: str


class SearchSuccessEnvelope(SearchSchema):
    success: Literal[True] = True
    data: list[SearchWorkData]
    meta: SearchResponseMeta


class SearchFacetValueData(SearchSchema):
    slug: str
    label: str
    count: int = Field(ge=0)

    @classmethod
    def from_projection(cls, item: SearchFacetValue) -> "SearchFacetValueData":
        return cls.model_validate(item)


class SearchFacetsData(SearchSchema):
    categories: list[SearchFacetValueData]
    tags: list[SearchFacetValueData]
    approximate: bool

    @classmethod
    def from_projection(cls, facets: SearchFacets) -> "SearchFacetsData":
        return cls(
            categories=[
                SearchFacetValueData.from_projection(item) for item in facets.categories
            ],
            tags=[SearchFacetValueData.from_projection(item) for item in facets.tags],
            approximate=facets.approximate,
        )
