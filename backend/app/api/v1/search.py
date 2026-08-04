from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.search.dependencies import (
    PublicSearchDependency,
    enforce_public_search_rate_limit,
)
from app.modules.search.errors import SearchFilterInvalidError
from app.modules.search.schemas import (
    AutocompleteSuggestionData,
    SearchFacetsData,
    SearchResponseMeta,
    SearchSuccessEnvelope,
    SearchWorkData,
)

router = APIRouter(
    prefix="/api/v1/public/search",
    tags=["public-search"],
    dependencies=[Depends(enforce_public_search_rate_limit)],
)

SEARCH_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {
        "description": "Search query, filter or sort is invalid.",
        "model": ErrorEnvelope,
    },
    429: {"description": "Search rate limit exceeded.", "model": ErrorEnvelope},
    503: {"description": "Search is temporarily unavailable.", "model": ErrorEnvelope},
}
ALLOWED_QUERY_PARAMETERS = frozenset(
    {
        "q",
        "category",
        "tags",
        "tagsMode",
        "organization",
        "publishedFrom",
        "publishedTo",
        "hasBlockchainProof",
        "certificateStatus",
        "sort",
        "cursor",
        "pageSize",
    }
)
FACET_QUERY_PARAMETERS = ALLOWED_QUERY_PARAMETERS - {"sort", "cursor", "pageSize"}
AUTOCOMPLETE_QUERY_PARAMETERS = frozenset({"q"})


@router.get(
    "/autocomplete",
    response_model=SuccessEnvelope[list[AutocompleteSuggestionData]],
    responses=SEARCH_RESPONSES,
)
async def public_search_autocomplete(
    request: Request,
    service: PublicSearchDependency,
    q: Annotated[str | None, Query(max_length=400)] = None,
) -> SuccessEnvelope[list[AutocompleteSuggestionData]]:
    if set(request.query_params) - AUTOCOMPLETE_QUERY_PARAMETERS:
        raise SearchFilterInvalidError("unknown_filter")
    suggestions = await service.autocomplete(query=q)
    return SuccessEnvelope(
        data=[AutocompleteSuggestionData.from_projection(item) for item in suggestions],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/facets",
    response_model=SuccessEnvelope[SearchFacetsData],
    responses=SEARCH_RESPONSES,
)
async def public_search_facets(
    request: Request,
    service: PublicSearchDependency,
    q: Annotated[str | None, Query(max_length=400)] = None,
    category: Annotated[str | None, Query(max_length=200)] = None,
    tags: Annotated[str | None, Query(max_length=1_700)] = None,
    tags_mode: Annotated[str, Query(alias="tagsMode", max_length=8)] = "any",
    organization: Annotated[str | None, Query(max_length=200)] = None,
    published_from: Annotated[
        str | None, Query(alias="publishedFrom", max_length=40)
    ] = None,
    published_to: Annotated[
        str | None, Query(alias="publishedTo", max_length=40)
    ] = None,
    has_blockchain_proof: Annotated[
        str | None, Query(alias="hasBlockchainProof", max_length=5)
    ] = None,
    certificate_status: Annotated[
        str | None, Query(alias="certificateStatus", max_length=16)
    ] = None,
) -> SuccessEnvelope[SearchFacetsData]:
    if set(request.query_params) - FACET_QUERY_PARAMETERS:
        raise SearchFilterInvalidError("unknown_filter")
    facets = await service.facets(
        query=q,
        category=category,
        tags=tags,
        tags_mode=tags_mode,
        organization=organization,
        published_from=published_from,
        published_to=published_to,
        has_blockchain_proof=has_blockchain_proof,
        certificate_status=certificate_status,
    )
    return SuccessEnvelope(
        data=SearchFacetsData.from_projection(facets),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "",
    response_model=SearchSuccessEnvelope,
    responses=SEARCH_RESPONSES,
)
async def public_search(
    request: Request,
    service: PublicSearchDependency,
    q: Annotated[str | None, Query(max_length=400)] = None,
    category: Annotated[str | None, Query(max_length=200)] = None,
    tags: Annotated[str | None, Query(max_length=1_700)] = None,
    tags_mode: Annotated[str, Query(alias="tagsMode", max_length=8)] = "any",
    organization: Annotated[str | None, Query(max_length=200)] = None,
    published_from: Annotated[
        str | None, Query(alias="publishedFrom", max_length=40)
    ] = None,
    published_to: Annotated[
        str | None, Query(alias="publishedTo", max_length=40)
    ] = None,
    has_blockchain_proof: Annotated[
        str | None, Query(alias="hasBlockchainProof", max_length=5)
    ] = None,
    certificate_status: Annotated[
        str | None, Query(alias="certificateStatus", max_length=16)
    ] = None,
    sort: Annotated[str | None, Query(max_length=32)] = None,
    cursor: Annotated[str | None, Query(max_length=1_024)] = None,
    page_size: Annotated[int, Query(alias="pageSize")] = 20,
) -> SearchSuccessEnvelope:
    unknown = set(request.query_params) - ALLOWED_QUERY_PARAMETERS
    if unknown:
        raise SearchFilterInvalidError("unknown_filter")
    result = await service.search(
        query=q,
        category=category,
        tags=tags,
        tags_mode=tags_mode,
        organization=organization,
        published_from=published_from,
        published_to=published_to,
        has_blockchain_proof=has_blockchain_proof,
        certificate_status=certificate_status,
        sort=sort,
        cursor=cursor,
        page_size=page_size,
        request_id=request.state.request_id,
    )
    return SearchSuccessEnvelope(
        data=[SearchWorkData.from_projection(item) for item in result.page.items],
        meta=SearchResponseMeta(
            request_id=request.state.request_id,
            next_cursor=result.page.next_cursor,
            duration_ms=result.duration_ms,
            version=result.version,
        ),
    )
