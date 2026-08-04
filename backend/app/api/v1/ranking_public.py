from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.public.dependencies import enforce_public_rate_limit
from app.modules.ranking.public_dependencies import PublicRankingServiceDependency
from app.modules.ranking.public_schemas import PublicRankingData

router = APIRouter(
    prefix="/api/v1/public/campaigns",
    tags=["public-ranking"],
    dependencies=[Depends(enforce_public_rate_limit)],
)


@router.get(
    "/{slug}/ranking",
    response_model=SuccessEnvelope[PublicRankingData],
    responses={
        404: {
            "description": "Published ranking was not found.",
            "model": ErrorEnvelope,
        },
    },
)
async def get_public_ranking(
    slug: Annotated[str, Path(min_length=1, max_length=180)],
    request: Request,
    service: PublicRankingServiceDependency,
    version: Annotated[int | None, Query(ge=1)] = None,
    category_id: Annotated[UUID | None, Query(alias="categoryId")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> SuccessEnvelope[PublicRankingData]:
    result = await service.get_ranking(
        campaign_slug=slug,
        version=version,
        category_id=category_id,
        page=page,
        page_size=page_size,
    )
    return SuccessEnvelope(
        data=PublicRankingData.from_view(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
