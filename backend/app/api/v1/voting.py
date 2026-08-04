from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.voting.dependencies import (
    VotingEligibilityServiceDependency,
    VotingServiceDependency,
    enforce_voting_rate_limit,
)
from app.modules.voting.schemas import (
    VoteChangeRequest,
    VoteMutationData,
    VotingEligibilityData,
)

router = APIRouter(prefix="/api/v1/campaigns", tags=["voting"])


@router.get(
    "/{campaign_id}/eligibility",
    response_model=SuccessEnvelope[VotingEligibilityData],
)
async def get_voting_eligibility(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: VotingEligibilityServiceDependency,
    work_id: Annotated[UUID | None, Query(alias="workId")] = None,
) -> SuccessEnvelope[VotingEligibilityData]:
    decision = await service.evaluate(
        principal,
        campaign_id,
        work_id=work_id,
    )
    return SuccessEnvelope(
        data=VotingEligibilityData.model_validate(decision),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{campaign_id}/works/{work_id}/votes",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[VoteMutationData],
    dependencies=[Depends(enforce_voting_rate_limit)],
)
async def create_vote(
    campaign_id: UUID,
    work_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
) -> SuccessEnvelope[VoteMutationData]:
    result = await service.create_vote(
        principal,
        campaign_id,
        work_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=VoteMutationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{campaign_id}/votes/change",
    response_model=SuccessEnvelope[VoteMutationData],
    dependencies=[Depends(enforce_voting_rate_limit)],
)
async def change_vote(
    campaign_id: UUID,
    payload: VoteChangeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
) -> SuccessEnvelope[VoteMutationData]:
    result = await service.change_vote(
        principal,
        campaign_id,
        payload.source_vote_id,
        payload.target_work_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=VoteMutationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/{campaign_id}/works/{work_id}/votes",
    response_model=SuccessEnvelope[VoteMutationData],
    dependencies=[Depends(enforce_voting_rate_limit)],
)
async def revoke_vote(
    campaign_id: UUID,
    work_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: VotingServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
) -> SuccessEnvelope[VoteMutationData]:
    result = await service.revoke_vote(
        principal,
        campaign_id,
        work_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=VoteMutationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
