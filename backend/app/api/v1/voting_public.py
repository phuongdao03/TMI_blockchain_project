from fastapi import APIRouter, Query, Request

from app.core.schemas import (
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.voting.dependencies import PublicVotingServiceDependency
from app.modules.voting.schemas import (
    PublicCampaignWorkData,
    PublicVoteSummaryData,
    PublicVotingCampaignData,
)

router = APIRouter(prefix="/api/v1/public/campaigns", tags=["public-voting"])


@router.get("", response_model=PaginatedSuccessEnvelope[list[PublicVotingCampaignData]])
async def list_public_campaigns(
    request: Request,
    service: PublicVotingServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[PublicVotingCampaignData]]:
    rows, total = await service.list_campaigns(page=page, page_size=page_size)
    return PaginatedSuccessEnvelope(
        data=[PublicVotingCampaignData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get("/{slug}", response_model=SuccessEnvelope[PublicVotingCampaignData])
async def get_public_campaign(
    slug: str,
    request: Request,
    service: PublicVotingServiceDependency,
) -> SuccessEnvelope[PublicVotingCampaignData]:
    row = await service.campaign(slug)
    return SuccessEnvelope(
        data=PublicVotingCampaignData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{slug}/works", response_model=SuccessEnvelope[list[PublicCampaignWorkData]]
)
async def list_public_campaign_works(
    slug: str,
    request: Request,
    service: PublicVotingServiceDependency,
) -> SuccessEnvelope[list[PublicCampaignWorkData]]:
    rows = await service.works(slug)
    return SuccessEnvelope(
        data=[PublicCampaignWorkData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{slug}/vote-summary",
    response_model=SuccessEnvelope[list[PublicVoteSummaryData]],
)
async def get_public_vote_summary(
    slug: str,
    request: Request,
    service: PublicVotingServiceDependency,
) -> SuccessEnvelope[list[PublicVoteSummaryData]]:
    rows = await service.summary(slug)
    return SuccessEnvelope(
        data=[PublicVoteSummaryData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )
