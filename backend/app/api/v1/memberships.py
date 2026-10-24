from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from pydantic import Field

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.memberships.catalog import MEMBER_TIER_COPY
from app.modules.memberships.service import MembershipService
from app.modules.payments.schemas import PaymentSchema

router = APIRouter(prefix="/api/v1", tags=["memberships"])


class PlanRequest(PaymentSchema):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    tier: Literal["SILVER", "COMPANION", "PRESTIGE"]
    amount_minor: Annotated[int, Field(strict=True, gt=0, le=1_000_000_000)]
    duration_days: Annotated[int, Field(strict=True, ge=1, le=3660)]
    description: Annotated[str, Field(min_length=1, max_length=500)]
    benefits: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=240)]],
        Field(min_length=1, max_length=20),
    ]
    conditions: Annotated[str, Field(max_length=1000)]


class PlanData(PaymentSchema):
    id: UUID
    name: str
    tier: Literal["SILVER", "COMPANION", "PRESTIGE"]
    amount_minor: int
    duration_days: int
    description: str
    benefits: list[str]
    conditions: str
    active: bool


class MemberTierCopyData(PaymentSchema):
    name: str
    description: str
    benefits: list[str]
    conditions: str


class PlanCatalogData(PaymentSchema):
    plans: list[PlanData]
    member: MemberTierCopyData


class MembershipData(PaymentSchema):
    tier: Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"]
    member_number: str
    status: Literal["ACTIVE", "FREE"]
    expires_at: datetime | None


class PurchaseData(PaymentSchema):
    id: UUID
    plan_id: UUID
    tier: str
    amount_minor: int
    list_price_minor: int
    credit_minor: int
    expires_at: datetime
    created_at: datetime


class MembershipOverview(MembershipData):
    plans: list[PlanData]
    purchases: list[PurchaseData]


class ChatRequest(PaymentSchema):
    body: Annotated[str, Field(min_length=1, max_length=2000)]


class ChatRoomAccessData(PaymentSchema):
    room: Literal["MEMBER", "COMPANION", "PRESTIGE"]
    allowed: bool
    source: Literal["TIER", "MANUAL", "ADMIN", "NONE"]


class ChatRoomUserCandidateData(PaymentSchema):
    user_id: UUID
    email: str
    display_name: str


class ChatRoomGrantData(ChatRoomUserCandidateData):
    room: Literal["MEMBER", "COMPANION", "PRESTIGE"]
    reason: str
    granted_at: datetime
    granted_by_user_id: UUID


class ChatRoomGrantRequest(PaymentSchema):
    user_id: UUID
    room: Literal["MEMBER", "COMPANION", "PRESTIGE"]
    reason: Annotated[str, Field(min_length=3, max_length=240)]


class ChatRoomGrantRevokeRequest(PaymentSchema):
    reason: Annotated[str, Field(min_length=3, max_length=240)]


class ChatMessageData(PaymentSchema):
    id: UUID
    display_name: str
    avatar_url: str | None
    body: str
    tier: str
    created_at: datetime
    can_remove: bool


class QuoteRequest(PaymentSchema):
    renewal_opt_in: bool = False


class QuoteData(PaymentSchema):
    plan_id: UUID
    name: str
    tier: Literal["SILVER", "COMPANION", "PRESTIGE"]
    kind: Literal["NEW", "UPGRADE", "RENEWAL"]
    from_tier: Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"]
    list_price_minor: int
    credit_minor: int
    amount_due_minor: int
    duration_days: int
    remaining_days: int
    expires_at: datetime
    approval_required: bool


class PurchaseRequest(PaymentSchema):
    expected_amount_minor: Annotated[int, Field(strict=True, ge=0, le=1_000_000_000)]
    renewal_opt_in: bool = False


class DiamondApplicationRequest(PaymentSchema):
    statement: Annotated[str, Field(min_length=1, max_length=5000)]


class DiamondApplicationData(PaymentSchema):
    id: UUID
    user_id: UUID
    statement: str
    status: Literal["PENDING", "INFO_REQUESTED", "APPROVED", "REJECTED"]
    decision_note: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DiamondApplicationListData(PaymentSchema):
    applications: list[DiamondApplicationData]


class DiamondApplicationReviewRequest(PaymentSchema):
    note: Annotated[str, Field(min_length=1, max_length=2000)]


class BenefitRequestCreate(PaymentSchema):
    benefit: Literal[
        "COLLABORATION_NEED",
        "ADVISORY_SESSION",
        "FACILITATED_INTRODUCTION",
        "MEMBER_STORY",
    ]
    statement: Annotated[str, Field(min_length=1, max_length=5000)]


class BenefitRequestData(PaymentSchema):
    id: UUID
    user_id: UUID
    benefit: Literal[
        "COLLABORATION_NEED",
        "ADVISORY_SESSION",
        "FACILITATED_INTRODUCTION",
        "MEMBER_STORY",
    ]
    cycle_started_at: datetime
    statement: str
    status: Literal["PENDING", "INFO_REQUESTED", "APPROVED", "COMPLETED", "REJECTED"]
    decision_note: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BenefitRequestListData(PaymentSchema):
    requests: list[BenefitRequestData]


class BenefitRequestReviewRequest(PaymentSchema):
    note: Annotated[str, Field(min_length=1, max_length=2000)]


class CollaborationNeedData(PaymentSchema):
    id: UUID
    display_name: str
    username: str | None
    statement: str
    created_at: datetime


class CollaborationNeedListData(PaymentSchema):
    requests: list[CollaborationNeedData]


@router.get("/memberships/plans", response_model=SuccessEnvelope[PlanCatalogData])
async def list_membership_plans(
    request: Request, session: SessionDependency
) -> SuccessEnvelope[PlanCatalogData]:
    async with session.begin():
        plans = await MembershipService(session).public_plans()
    return SuccessEnvelope(
        data=PlanCatalogData(
            plans=[PlanData.model_validate(plan) for plan in plans],
            member=MemberTierCopyData.model_validate(MEMBER_TIER_COPY),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete("/admin/membership-plans/{plan_id}")
async def retire_plan(
    plan_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[dict[str, str]]:
    await MembershipService(session).retire_plan(principal, plan_id)
    return SuccessEnvelope(
        data={"status": "retired"},
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete("/community/chat/messages/{message_id}")
async def remove_chat_message(
    message_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[dict[str, str]]:
    await MembershipService(session).remove_message(principal, message_id)
    return SuccessEnvelope(
        data={"status": "removed"},
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/memberships/me", response_model=SuccessEnvelope[MembershipOverview])
async def get_membership(
    request: Request, principal: CurrentPrincipalDependency, session: SessionDependency
) -> SuccessEnvelope[MembershipOverview]:
    result = await MembershipService(session).overview(principal.user_id)
    return SuccessEnvelope(
        data=MembershipOverview.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/memberships/plans/{plan_id}/purchases",
    response_model=SuccessEnvelope[MembershipData],
)
async def buy_membership(
    plan_id: UUID,
    payload: PurchaseRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> SuccessEnvelope[MembershipData]:
    result = await MembershipService(session).purchase(
        principal.user_id,
        plan_id,
        idempotency_key,
        expected_amount_minor=payload.expected_amount_minor,
        renewal_opt_in=payload.renewal_opt_in,
    )
    return SuccessEnvelope(
        data=MembershipData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/memberships/plans/{plan_id}/quote",
    response_model=SuccessEnvelope[QuoteData],
)
async def quote_membership(
    plan_id: UUID,
    payload: QuoteRequest,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[QuoteData]:
    result = await MembershipService(session).quote(
        principal.user_id,
        plan_id,
        renewal_opt_in=payload.renewal_opt_in,
    )
    return SuccessEnvelope(
        data=QuoteData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/memberships/diamond-applications",
    response_model=SuccessEnvelope[DiamondApplicationData],
)
async def submit_diamond_application(
    payload: DiamondApplicationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[DiamondApplicationData]:
    result = await MembershipService(session).submit_diamond_application(
        principal, payload.statement
    )
    return SuccessEnvelope(
        data=DiamondApplicationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/memberships/diamond-applications/me",
    response_model=SuccessEnvelope[DiamondApplicationListData],
)
async def my_diamond_applications(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[DiamondApplicationListData]:
    rows = await MembershipService(session).my_diamond_applications(principal.user_id)
    return SuccessEnvelope(
        data=DiamondApplicationListData(
            applications=[DiamondApplicationData.model_validate(row) for row in rows]
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/memberships/diamond-applications",
    response_model=SuccessEnvelope[DiamondApplicationListData],
)
async def list_diamond_applications(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    status: Literal["PENDING", "INFO_REQUESTED", "APPROVED", "REJECTED"] | None = None,
    limit: Annotated[int, Field(ge=1, le=200)] = 100,
) -> SuccessEnvelope[DiamondApplicationListData]:
    rows = await MembershipService(session).list_diamond_applications(
        principal, status=status, limit=limit
    )
    return SuccessEnvelope(
        data=DiamondApplicationListData(
            applications=[DiamondApplicationData.model_validate(row) for row in rows]
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/memberships/diamond-applications/{application_id}/{action}",
    response_model=SuccessEnvelope[DiamondApplicationData],
)
async def review_diamond_application(
    application_id: UUID,
    action: Literal["approve", "reject", "request-info"],
    payload: DiamondApplicationReviewRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[DiamondApplicationData]:
    decision = {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "request-info": "INFO_REQUESTED",
    }[action]
    result = await MembershipService(session).review_diamond_application(
        principal, application_id, decision=decision, note=payload.note
    )
    return SuccessEnvelope(
        data=DiamondApplicationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/memberships/benefit-requests/me",
    response_model=SuccessEnvelope[BenefitRequestListData],
)
async def my_benefit_requests(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[BenefitRequestListData]:
    rows = await MembershipService(session).my_benefit_requests(principal.user_id)
    return SuccessEnvelope(
        data=BenefitRequestListData(
            requests=[BenefitRequestData.model_validate(row) for row in rows]
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/memberships/benefit-requests",
    response_model=SuccessEnvelope[BenefitRequestData],
)
async def submit_benefit_request(
    payload: BenefitRequestCreate,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[BenefitRequestData]:
    result = await MembershipService(session).submit_benefit_request(
        principal, benefit=payload.benefit, statement=payload.statement
    )
    return SuccessEnvelope(
        data=BenefitRequestData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/memberships/collaboration-needs",
    response_model=SuccessEnvelope[CollaborationNeedListData],
)
async def collaboration_needs(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CollaborationNeedListData]:
    rows = await MembershipService(session).collaboration_needs(principal)
    return SuccessEnvelope(
        data=CollaborationNeedListData(
            requests=[CollaborationNeedData.model_validate(row) for row in rows]
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/memberships/benefit-requests",
    response_model=SuccessEnvelope[BenefitRequestListData],
)
async def list_benefit_requests(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    status: Literal["PENDING", "INFO_REQUESTED", "APPROVED", "COMPLETED", "REJECTED"]
    | None = None,
    limit: Annotated[int, Field(ge=1, le=200)] = 100,
) -> SuccessEnvelope[BenefitRequestListData]:
    rows = await MembershipService(session).list_benefit_requests(
        principal, status=status, limit=limit
    )
    return SuccessEnvelope(
        data=BenefitRequestListData(
            requests=[BenefitRequestData.model_validate(row) for row in rows]
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/memberships/benefit-requests/{request_id}/{action}",
    response_model=SuccessEnvelope[BenefitRequestData],
)
async def review_benefit_request(
    request_id: UUID,
    action: Literal["approve", "reject", "request-info", "complete"],
    payload: BenefitRequestReviewRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[BenefitRequestData]:
    result = await MembershipService(session).review_benefit_request(
        principal, request_id, decision=action, note=payload.note
    )
    return SuccessEnvelope(
        data=BenefitRequestData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/admin/membership-plans", response_model=SuccessEnvelope[PlanData])
async def publish_plan(
    payload: PlanRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PlanData]:
    result = await MembershipService(session).publish(principal, **payload.model_dump())
    return SuccessEnvelope(
        data=PlanData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/memberships/chat-access/users",
    response_model=SuccessEnvelope[list[ChatRoomUserCandidateData]],
)
async def search_chat_access_users(
    q: Annotated[str, Query(min_length=2, max_length=160)],
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[ChatRoomUserCandidateData]]:
    users = await MembershipService(session).chat_access_candidates(principal, q)
    return SuccessEnvelope(
        data=[ChatRoomUserCandidateData.model_validate(user) for user in users],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/memberships/chat-access",
    response_model=SuccessEnvelope[list[ChatRoomGrantData]],
)
async def list_chat_access_grants(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    room: Literal["MEMBER", "COMPANION", "PRESTIGE"] | None = None,
) -> SuccessEnvelope[list[ChatRoomGrantData]]:
    grants = await MembershipService(session).list_chat_room_access(
        principal, room=room
    )
    return SuccessEnvelope(
        data=[ChatRoomGrantData.model_validate(grant) for grant in grants],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/memberships/chat-access",
    status_code=201,
    response_model=SuccessEnvelope[ChatRoomGrantData],
)
async def grant_chat_access(
    payload: ChatRoomGrantRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[ChatRoomGrantData]:
    grant = await MembershipService(session).grant_chat_room_access(
        principal,
        payload.user_id,
        payload.room,
        payload.reason,
    )
    return SuccessEnvelope(
        data=ChatRoomGrantData.model_validate(grant),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/admin/memberships/chat-access/{room}/{user_id}",
    response_model=SuccessEnvelope[ChatRoomGrantData],
)
async def revoke_chat_access(
    room: Literal["MEMBER", "COMPANION", "PRESTIGE"],
    user_id: UUID,
    payload: ChatRoomGrantRevokeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[ChatRoomGrantData]:
    grant = await MembershipService(session).revoke_chat_room_access(
        principal, user_id, room, payload.reason
    )
    return SuccessEnvelope(
        data=ChatRoomGrantData.model_validate(grant),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/community/chat/{room}/access",
    response_model=SuccessEnvelope[ChatRoomAccessData],
)
async def get_chat_access(
    room: Literal["MEMBER", "COMPANION", "PRESTIGE"],
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[ChatRoomAccessData]:
    access = await MembershipService(session).chat_access(principal, room)
    return SuccessEnvelope(
        data=ChatRoomAccessData.model_validate(access),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/community/chat/{room}/messages",
    response_model=SuccessEnvelope[list[ChatMessageData]],
)
async def get_chat(
    room: Literal["MEMBER", "COMPANION", "PRESTIGE"],
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[ChatMessageData]]:
    result = await MembershipService(session).chat(principal, room)
    return SuccessEnvelope(
        data=[ChatMessageData.model_validate(item) for item in result],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/community/chat/{room}/messages",
    response_model=SuccessEnvelope[list[ChatMessageData]],
)
async def send_chat(
    room: Literal["MEMBER", "COMPANION", "PRESTIGE"],
    payload: ChatRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[ChatMessageData]]:
    result = await MembershipService(session).chat(principal, room, payload.body)
    return SuccessEnvelope(
        data=[ChatMessageData.model_validate(item) for item in result],
        meta=ResponseMeta(request_id=request.state.request_id),
    )
