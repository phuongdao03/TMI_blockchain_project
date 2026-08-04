from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import CsrfProtectedPrincipalDependency
from app.modules.ranking.publish_dependencies import RankingPublicationServiceDependency
from app.modules.ranking.publish_schemas import (
    RankingPublicationData,
    RankingPublishRequest,
)

router = APIRouter(
    prefix="/api/v1/admin/ranking/campaigns",
    tags=["ranking-admin"],
)

RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Ranking publication is forbidden.", "model": ErrorEnvelope},
    404: {
        "description": "Campaign or ranking snapshot not found.",
        "model": ErrorEnvelope,
    },
    409: {
        "description": "Campaign is not ready for publication.",
        "model": ErrorEnvelope,
    },
}


@router.post(
    "/{campaign_id}/publish",
    response_model=SuccessEnvelope[RankingPublicationData],
    responses=RESPONSES,
)
async def publish_ranking_results(
    campaign_id: UUID,
    payload: RankingPublishRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: RankingPublicationServiceDependency,
) -> SuccessEnvelope[RankingPublicationData]:
    result = await service.publish(
        principal,
        campaign_id,
        version=payload.version,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=RankingPublicationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
