import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.search.dependencies import enforce_public_search_rate_limit
from app.modules.search.discovery_dependencies import SearchDiscoveryDependency
from app.modules.search.discovery_models import SearchSnapshotPeriod
from app.modules.search.discovery_schemas import (
    RelatedWorkData,
    SearchAnalyticsData,
    SearchClickData,
    SearchClickRequest,
    SearchSuppressionData,
    SearchSuppressionRequest,
    TrendingSearchData,
)

router = APIRouter(prefix="/api/v1", tags=["search-discovery"])


@router.get(
    "/public/discovery/trending",
    response_model=SuccessEnvelope[list[TrendingSearchData]],
    dependencies=[Depends(enforce_public_search_rate_limit)],
)
async def public_trending(
    request: Request,
    service: SearchDiscoveryDependency,
    period: SearchSnapshotPeriod = SearchSnapshotPeriod.DAILY,
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
) -> SuccessEnvelope[list[TrendingSearchData]]:
    rows = await service.trending(period=period, limit=limit)
    return SuccessEnvelope(
        data=[TrendingSearchData.from_view(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/public/works/{slug}/related",
    response_model=SuccessEnvelope[list[RelatedWorkData]],
    dependencies=[Depends(enforce_public_search_rate_limit)],
)
async def public_related(
    slug: str,
    request: Request,
    service: SearchDiscoveryDependency,
    limit: Annotated[int, Query(ge=1, le=12)] = 6,
) -> SuccessEnvelope[list[RelatedWorkData]]:
    rows = await service.related(slug=slug, limit=limit)
    return SuccessEnvelope(
        data=[RelatedWorkData.from_view(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/public/search/clicks",
    response_model=SuccessEnvelope[SearchClickData],
    dependencies=[Depends(enforce_public_search_rate_limit)],
)
async def public_search_click(
    payload: SearchClickRequest, request: Request, service: SearchDiscoveryDependency
) -> SuccessEnvelope[SearchClickData]:
    recorded = await service.record_click(
        request_id=payload.request_id, work_id=payload.work_id
    )
    return SuccessEnvelope(
        data=SearchClickData(recorded=recorded),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/search/analytics", response_model=SuccessEnvelope[SearchAnalyticsData]
)
async def admin_search_analytics(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: SearchDiscoveryDependency,
    start: datetime,
    end: datetime,
    category: Annotated[str | None, Query(max_length=180)] = None,
) -> SuccessEnvelope[SearchAnalyticsData]:
    summary = await service.analytics(
        principal, start=start, end=end, category=category
    )
    return SuccessEnvelope(
        data=SearchAnalyticsData.from_summary(summary),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/admin/search/analytics/export", response_class=Response)
async def admin_search_analytics_export(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: SearchDiscoveryDependency,
    start: datetime,
    end: datetime,
    category: Annotated[str | None, Query(max_length=180)] = None,
) -> Response:
    summary = await service.analytics(
        principal, start=start, end=end, category=category
    )
    await service.audit_export(
        principal,
        request_id=request.state.request_id,
        start=start,
        end=end,
        category=category,
    )
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "period_start",
            "category_slug",
            "search_count",
            "zero_result_count",
            "click_count",
            "latency_p95_ms",
        ]
    )
    for point in summary.points:
        writer.writerow(
            [
                point.period_start.isoformat(),
                point.category_slug or "",
                point.search_count,
                point.zero_result_count,
                point.click_count,
                point.latency_p95_ms,
            ]
        )
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=search-analytics.csv"},
    )


@router.put(
    "/admin/search/trending/{query_hash}",
    response_model=SuccessEnvelope[SearchSuppressionData],
)
async def admin_suppress_trending(
    query_hash: str,
    payload: SearchSuppressionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: SearchDiscoveryDependency,
) -> SuccessEnvelope[SearchSuppressionData]:
    await service.suppress(
        principal,
        query_hash=query_hash,
        reason=payload.reason,
        suppressed=payload.suppressed,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=SearchSuppressionData(
            query_hash=query_hash, suppressed=payload.suppressed
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
