from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.schemas import ListResponseMeta, PaginatedSuccessEnvelope
from app.modules.auth.dependencies import CurrentPrincipalDependency
from app.modules.voting.dependencies import VoteHistoryServiceDependency
from app.modules.voting.models import VoteStatus
from app.modules.voting.schemas import VoteHistoryData

router = APIRouter(prefix="/api/v1/me/votes", tags=["voting"])


@router.get("", response_model=PaginatedSuccessEnvelope[list[VoteHistoryData]])
async def list_my_votes(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: VoteHistoryServiceDependency,
    campaign_id: Annotated[UUID | None, Query(alias="campaignId")] = None,
    vote_status: Annotated[VoteStatus | None, Query(alias="status")] = None,
    date_from: Annotated[datetime | None, Query(alias="dateFrom")] = None,
    date_to: Annotated[datetime | None, Query(alias="dateTo")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[VoteHistoryData]]:
    rows, total = await service.list(
        principal,
        campaign_id=campaign_id,
        status=vote_status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[VoteHistoryData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )
