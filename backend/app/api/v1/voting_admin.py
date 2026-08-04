import csv
import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import StreamingResponse

from app.core.schemas import (
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.voting.dependencies import (
    AdminVoteServiceDependency,
    VotingCampaignServiceDependency,
)
from app.modules.voting.models import CampaignStatus, CampaignWorkStatus, VoteStatus
from app.modules.voting.schemas import (
    AdminVoteData,
    CampaignLifecycleReasonRequest,
    CampaignParticipantBulkRequest,
    CampaignParticipantData,
    CampaignParticipantRequest,
    VotingCampaignData,
    VotingCampaignRequest,
)
from app.modules.voting.service import (
    CampaignLifecycleAction,
    VotingCampaignInput,
    VotingCampaignService,
)

router = APIRouter(prefix="/api/v1/admin/voting/campaigns", tags=["voting-admin"])


@router.get(
    "/{campaign_id}/votes",
    response_model=PaginatedSuccessEnvelope[list[AdminVoteData]],
)
async def list_campaign_votes(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: AdminVoteServiceDependency,
    work_id: Annotated[UUID | None, Query(alias="workId")] = None,
    vote_status: Annotated[VoteStatus | None, Query(alias="status")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[AdminVoteData]]:
    rows, total = await service.list(
        principal,
        campaign_id,
        work_id=work_id,
        status=vote_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[AdminVoteData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get("/{campaign_id}/votes/export.csv", response_class=StreamingResponse)
async def export_campaign_votes(
    campaign_id: UUID,
    principal: CurrentPrincipalDependency,
    service: AdminVoteServiceDependency,
    work_id: Annotated[UUID | None, Query(alias="workId")] = None,
    vote_status: Annotated[VoteStatus | None, Query(alias="status")] = None,
) -> StreamingResponse:
    rows, _ = await service.list(
        principal,
        campaign_id,
        work_id=work_id,
        status=vote_status,
        page=1,
        page_size=10_000,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ("vote_id", "campaign_id", "work_id", "voter_reference", "status", "created_at")
    )
    writer.writerows(
        (
            str(row.vote_id),
            str(row.campaign_id),
            str(row.work_id),
            row.voter_reference,
            row.status.value,
            row.created_at.isoformat(),
        )
        for row in rows
    )
    return StreamingResponse(
        iter((buffer.getvalue(),)),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="votes-{campaign_id}.csv"'
        },
    )


def _input(payload: VotingCampaignRequest) -> VotingCampaignInput:
    return VotingCampaignInput(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        campaign_type=payload.campaign_type,
        period_type=payload.period_type,
        timezone=payload.timezone,
        start_at=payload.start_at,
        end_at=payload.end_at,
        max_votes_per_user=payload.max_votes_per_user,
        max_votes_per_work_per_user=payload.max_votes_per_work_per_user,
        allow_vote_change=payload.allow_vote_change,
        allow_vote_revoke=payload.allow_vote_revoke,
        require_verified_email=payload.require_verified_email,
        min_account_age_hours=payload.min_account_age_hours,
        eligibility_rules=payload.eligibility_rules.model_dump(
            mode="json",
            by_alias=False,
        ),
    )


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[VotingCampaignData]],
)
async def list_campaigns(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: VotingCampaignServiceDependency,
    campaign_status: Annotated[
        CampaignStatus | None,
        Query(alias="status"),
    ] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[VotingCampaignData]]:
    rows, total = await service.list(
        principal,
        status=campaign_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[VotingCampaignData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[VotingCampaignData],
)
async def create_campaign(
    payload: VotingCampaignRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    row = await service.create(
        principal,
        _input(payload),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=VotingCampaignData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/{campaign_id}", response_model=SuccessEnvelope[VotingCampaignData])
async def get_campaign(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    row = await service.get(principal, campaign_id)
    return SuccessEnvelope(
        data=VotingCampaignData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put("/{campaign_id}", response_model=SuccessEnvelope[VotingCampaignData])
async def update_campaign(
    campaign_id: UUID,
    payload: VotingCampaignRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    row = await service.update(
        principal,
        campaign_id,
        _input(payload),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=VotingCampaignData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{campaign_id}/participants",
    response_model=PaginatedSuccessEnvelope[list[CampaignParticipantData]],
)
async def list_campaign_participants(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: VotingCampaignServiceDependency,
    participant_status: Annotated[
        CampaignWorkStatus | None,
        Query(alias="status"),
    ] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[CampaignParticipantData]]:
    rows, total = await service.list_participants(
        principal,
        campaign_id,
        status=participant_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[CampaignParticipantData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/{campaign_id}/participants",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CampaignParticipantData],
)
async def add_campaign_participant(
    campaign_id: UUID,
    payload: CampaignParticipantRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[CampaignParticipantData]:
    row = await service.add_participant(
        principal,
        campaign_id,
        payload.work_id,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CampaignParticipantData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{campaign_id}/participants/bulk",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[list[CampaignParticipantData]],
)
async def bulk_add_campaign_participants(
    campaign_id: UUID,
    payload: CampaignParticipantBulkRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[list[CampaignParticipantData]]:
    rows = await service.add_participants(
        principal,
        campaign_id,
        tuple(payload.work_ids),
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=[CampaignParticipantData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


async def _participant_transition_response(
    *,
    campaign_id: UUID,
    participant_id: UUID,
    action: str,
    reason: str,
    request: Request,
    principal: AuthPrincipal,
    service: VotingCampaignService,
) -> SuccessEnvelope[CampaignParticipantData]:
    method = (
        service.approve_participant
        if action == "approve"
        else service.remove_participant
    )
    row = await method(
        principal,
        campaign_id,
        participant_id,
        reason=reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CampaignParticipantData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{campaign_id}/participants/{participant_id}/approve",
    response_model=SuccessEnvelope[CampaignParticipantData],
)
async def approve_campaign_participant(
    campaign_id: UUID,
    participant_id: UUID,
    payload: CampaignLifecycleReasonRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[CampaignParticipantData]:
    return await _participant_transition_response(
        campaign_id=campaign_id,
        participant_id=participant_id,
        action="approve",
        reason=payload.reason,
        request=request,
        principal=principal,
        service=service,
    )


@router.post(
    "/{campaign_id}/participants/{participant_id}/remove",
    response_model=SuccessEnvelope[CampaignParticipantData],
)
async def remove_campaign_participant(
    campaign_id: UUID,
    participant_id: UUID,
    payload: CampaignLifecycleReasonRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[CampaignParticipantData]:
    return await _participant_transition_response(
        campaign_id=campaign_id,
        participant_id=participant_id,
        action="remove",
        reason=payload.reason,
        request=request,
        principal=principal,
        service=service,
    )


async def _transition_response(
    *,
    campaign_id: UUID,
    action: CampaignLifecycleAction,
    request: Request,
    principal: AuthPrincipal,
    service: VotingCampaignService,
    reason: str | None = None,
) -> SuccessEnvelope[VotingCampaignData]:
    row = await service.transition(
        principal,
        campaign_id,
        action,
        reason=reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=VotingCampaignData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{campaign_id}/schedule",
    response_model=SuccessEnvelope[VotingCampaignData],
)
async def schedule_campaign(
    campaign_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    return await _transition_response(
        campaign_id=campaign_id,
        action=CampaignLifecycleAction.SCHEDULE,
        request=request,
        principal=principal,
        service=service,
    )


@router.post(
    "/{campaign_id}/activate",
    response_model=SuccessEnvelope[VotingCampaignData],
)
async def activate_campaign(
    campaign_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    return await _transition_response(
        campaign_id=campaign_id,
        action=CampaignLifecycleAction.ACTIVATE,
        request=request,
        principal=principal,
        service=service,
    )


@router.post(
    "/{campaign_id}/pause",
    response_model=SuccessEnvelope[VotingCampaignData],
)
async def pause_campaign(
    campaign_id: UUID,
    payload: CampaignLifecycleReasonRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    return await _transition_response(
        campaign_id=campaign_id,
        action=CampaignLifecycleAction.PAUSE,
        request=request,
        principal=principal,
        service=service,
        reason=payload.reason,
    )


@router.post(
    "/{campaign_id}/resume",
    response_model=SuccessEnvelope[VotingCampaignData],
)
async def resume_campaign(
    campaign_id: UUID,
    payload: CampaignLifecycleReasonRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    return await _transition_response(
        campaign_id=campaign_id,
        action=CampaignLifecycleAction.RESUME,
        request=request,
        principal=principal,
        service=service,
        reason=payload.reason,
    )


@router.post(
    "/{campaign_id}/end",
    response_model=SuccessEnvelope[VotingCampaignData],
)
async def end_campaign(
    campaign_id: UUID,
    payload: CampaignLifecycleReasonRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    return await _transition_response(
        campaign_id=campaign_id,
        action=CampaignLifecycleAction.END,
        request=request,
        principal=principal,
        service=service,
        reason=payload.reason,
    )


@router.post(
    "/{campaign_id}/cancel",
    response_model=SuccessEnvelope[VotingCampaignData],
)
async def cancel_campaign(
    campaign_id: UUID,
    payload: CampaignLifecycleReasonRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingCampaignServiceDependency,
) -> SuccessEnvelope[VotingCampaignData]:
    return await _transition_response(
        campaign_id=campaign_id,
        action=CampaignLifecycleAction.CANCEL,
        request=request,
        principal=principal,
        service=service,
        reason=payload.reason,
    )
