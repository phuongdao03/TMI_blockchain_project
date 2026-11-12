from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.core.errors import DomainError
from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.billing.fees import FeePolicyService
from app.modules.billing.schemas import (
    CancelFeePolicyRequest,
    CreateFeePolicyRequest,
    DecideFeeWaiverRequest,
    FeePolicyData,
    FeeWaiverData,
    GrantFeeWaiverRequest,
    RequestFeeWaiverRequest,
)

router = APIRouter(prefix="/api/v1/admin", tags=["billing"])


class BillingForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="BILLING_FORBIDDEN",
            message="Fee management access is forbidden.",
            status_code=403,
        )


def _require(principal: AuthPrincipal, permission: str) -> None:
    AuthorizationPolicy.require_capability(
        principal,
        PolicyRequirement(permission=permission),
        BillingForbiddenError,
    )


def _require_any(principal: AuthPrincipal, permissions: tuple[str, ...]) -> None:
    if not any(
        AuthorizationPolicy.allows_capability(
            principal, PolicyRequirement(permission=permission)
        )
        for permission in permissions
    ):
        raise BillingForbiddenError()


@router.get(
    "/fee-policies",
    response_model=SuccessEnvelope[list[FeePolicyData]],
    responses={
        401: {"description": "Authentication is required.", "model": ErrorEnvelope},
        403: {
            "description": "Fee management access is forbidden.",
            "model": ErrorEnvelope,
        },
    },
)
async def list_fee_policies(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SuccessEnvelope[list[FeePolicyData]]:
    _require_any(
        principal,
        (
            "billing.fees.read",
            "billing.fees.policies.create",
            "billing.fees.policies.approve",
            "billing.fees.policies.cancel",
        ),
    )
    service = FeePolicyService(session)
    rows = await service.list_policies(
        at=service.current_time(), offset=offset, limit=limit
    )
    return SuccessEnvelope(
        data=[FeePolicyData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/fee-policies",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[FeePolicyData],
    responses={
        401: {"description": "Authentication is required.", "model": ErrorEnvelope},
        403: {
            "description": "Fee policy creation is forbidden.",
            "model": ErrorEnvelope,
        },
        409: {
            "description": "Fee policy conflicts with its effective scope.",
            "model": ErrorEnvelope,
        },
    },
)
async def create_fee_policy(
    payload: CreateFeePolicyRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[FeePolicyData]:
    _require(principal, "billing.fees.policies.create")
    policy = await FeePolicyService(session).create_draft(
        actor_user_id=principal.user_id,
        fee_type=payload.fee_type,
        dossier_type_id=payload.dossier_type_id,
        amount_minor=payload.amount_minor,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        display_name=payload.display_name,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=FeePolicyData.model_validate(policy),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/fee-policies/{policy_id}/approve",
    response_model=SuccessEnvelope[FeePolicyData],
    responses={
        401: {"description": "Authentication is required.", "model": ErrorEnvelope},
        403: {
            "description": "Fee policy approval is forbidden.",
            "model": ErrorEnvelope,
        },
        409: {
            "description": "Fee policy conflicts with its effective scope.",
            "model": ErrorEnvelope,
        },
    },
)
async def approve_fee_policy(
    policy_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[FeePolicyData]:
    _require(principal, "billing.fees.policies.approve")
    policy = await FeePolicyService(session).approve(
        policy_id, actor_user_id=principal.user_id
    )
    return SuccessEnvelope(
        data=FeePolicyData.model_validate(policy),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/fee-policies/{policy_id}/cancel",
    response_model=SuccessEnvelope[FeePolicyData],
    responses={
        401: {"description": "Authentication is required.", "model": ErrorEnvelope},
        403: {
            "description": "Fee policy cancellation is forbidden.",
            "model": ErrorEnvelope,
        },
        409: {"description": "Fee policy cannot be cancelled.", "model": ErrorEnvelope},
    },
)
async def cancel_fee_policy(
    policy_id: UUID,
    payload: CancelFeePolicyRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[FeePolicyData]:
    _require(principal, "billing.fees.policies.cancel")
    policy = await FeePolicyService(session).cancel(
        policy_id,
        actor_user_id=principal.user_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=FeePolicyData.model_validate(policy),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/fee-waivers",
    response_model=SuccessEnvelope[list[FeeWaiverData]],
)
async def list_fee_waivers(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SuccessEnvelope[list[FeeWaiverData]]:
    _require_any(
        principal,
        (
            "billing.fees.read",
            "billing.fees.waivers.approve",
        ),
    )
    waivers = await FeePolicyService(session).list_waivers(offset=offset, limit=limit)
    return SuccessEnvelope(
        data=[FeeWaiverData.model_validate(row) for row in waivers],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/fee-waivers",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[FeeWaiverData],
)
async def request_fee_waiver(
    payload: RequestFeeWaiverRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[FeeWaiverData]:
    _require(principal, "billing.fees.waivers.request")
    waiver = await FeePolicyService(session).request_waiver(
        dossier_id=payload.dossier_id,
        fee_type=payload.fee_type,
        amount_minor=payload.amount_minor,
        reason=payload.reason,
        actor_user_id=principal.user_id,
    )
    return SuccessEnvelope(
        data=FeeWaiverData.model_validate(waiver),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/fee-waivers/grant",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[FeeWaiverData],
)
async def grant_fee_waiver(
    payload: GrantFeeWaiverRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[FeeWaiverData]:
    _require(principal, "billing.fees.waivers.approve")
    waiver = await FeePolicyService(session).grant_submission_waiver(
        dossier_id=payload.dossier_id,
        reason=payload.reason,
        actor_user_id=principal.user_id,
    )
    return SuccessEnvelope(
        data=FeeWaiverData.model_validate(waiver),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/fee-waivers/{waiver_id}/approve",
    response_model=SuccessEnvelope[FeeWaiverData],
)
async def approve_fee_waiver(
    waiver_id: UUID,
    payload: DecideFeeWaiverRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[FeeWaiverData]:
    _require(principal, "billing.fees.waivers.approve")
    waiver = await FeePolicyService(session).decide_waiver(
        waiver_id,
        actor_user_id=principal.user_id,
        approve=True,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=FeeWaiverData.model_validate(waiver),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/fee-waivers/{waiver_id}/reject",
    response_model=SuccessEnvelope[FeeWaiverData],
)
async def reject_fee_waiver(
    waiver_id: UUID,
    payload: DecideFeeWaiverRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[FeeWaiverData]:
    _require(principal, "billing.fees.waivers.approve")
    waiver = await FeePolicyService(session).decide_waiver(
        waiver_id,
        actor_user_id=principal.user_id,
        approve=False,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=FeeWaiverData.model_validate(waiver),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
