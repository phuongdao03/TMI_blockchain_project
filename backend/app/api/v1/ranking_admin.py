from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import CsrfProtectedPrincipalDependency
from app.modules.ranking.recount_dependencies import RankingRecountServiceDependency
from app.modules.ranking.recount_schemas import RankingRecountData

router = APIRouter(
    prefix="/api/v1/admin/ranking/campaigns",
    tags=["ranking-admin"],
)

RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Ranking recount is forbidden.", "model": ErrorEnvelope},
}


@router.post(
    "/{campaign_id}/recount",
    status_code=202,
    response_model=SuccessEnvelope[RankingRecountData],
    responses=RESPONSES,
)
async def request_ranking_recount(
    campaign_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: RankingRecountServiceDependency,
) -> SuccessEnvelope[RankingRecountData]:
    result = await service.request(
        principal,
        campaign_id,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=RankingRecountData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
