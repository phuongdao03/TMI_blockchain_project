from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import Field

from app.core.schemas import (
    ErrorEnvelope,
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.events.models import CommunityEvent, CommunityEventRegistration
from app.modules.events.service import CommunityEventService
from app.modules.payments.schemas import PaymentSchema

router = APIRouter(prefix="/api/v1", tags=["community-events"])
admin_router = APIRouter(prefix="/api/v1/admin/events", tags=["community-events-admin"])


class EventCreateRequest(PaymentSchema):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(min_length=1, max_length=20000)]
    starts_at: datetime
    ends_at: datetime
    registration_opens_at: datetime | None = None
    priority_tier: Literal["COMPANION", "PRESTIGE"] | None = None
    priority_opens_at: datetime | None = None
    location: Annotated[str, Field(min_length=1, max_length=300)]
    required_tier: Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"]
    capacity: Annotated[int, Field(strict=True, ge=1, le=100000)]
    ticket_price_minor: Annotated[int, Field(strict=True, ge=0, le=1_000_000_000)] = 0
    cancellation_cutoff_at: datetime | None = None
    included_entitlement: Literal["TALK", "CONNECT", "CIRCLE"] | None = None
    entitlement_quota: Annotated[int | None, Field(strict=True, ge=1, le=100000)] = None
    requires_diamond_approval: bool = False


class EventUpdateRequest(PaymentSchema):
    title: Annotated[str | None, Field(min_length=1, max_length=200)] = None
    description: Annotated[str | None, Field(min_length=1, max_length=20000)] = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    registration_opens_at: datetime | None = None
    priority_tier: Literal["COMPANION", "PRESTIGE"] | None = None
    priority_opens_at: datetime | None = None
    location: Annotated[str | None, Field(min_length=1, max_length=300)] = None
    required_tier: Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"] | None = None
    capacity: Annotated[int | None, Field(strict=True, ge=1, le=100000)] = None
    ticket_price_minor: Annotated[
        int | None, Field(strict=True, ge=0, le=1_000_000_000)
    ] = None
    cancellation_cutoff_at: datetime | None = None
    included_entitlement: Literal["TALK", "CONNECT", "CIRCLE"] | None = None
    entitlement_quota: Annotated[int | None, Field(strict=True, ge=1, le=100000)] = None
    requires_diamond_approval: bool | None = None


class EventData(PaymentSchema):
    id: UUID
    title: str
    description: str
    starts_at: datetime
    ends_at: datetime
    registration_opens_at: datetime | None
    priority_tier: Literal["COMPANION", "PRESTIGE"] | None
    priority_opens_at: datetime | None
    location: str
    required_tier: Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"]
    capacity: int
    confirmed_count: int
    ticket_price_minor: int
    cancellation_cutoff_at: datetime | None
    included_entitlement: Literal["TALK", "CONNECT", "CIRCLE"] | None
    entitlement_quota: int | None
    requires_diamond_approval: bool
    status: Literal["DRAFT", "PUBLISHED", "CANCELLED"]
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class EventListData(PaymentSchema):
    events: list[EventData]


class EventRegistrationData(PaymentSchema):
    id: UUID
    event_id: UUID
    user_id: UUID
    status: Literal[
        "CONFIRMED",
        "WAITLISTED",
        "CANCELLED",
        "CANCELLED_LATE",
        "CANCELLED_BY_EVENT",
        "INELIGIBLE",
        "PAYMENT_REQUIRED",
    ]
    entitlement_units: int
    entitlement_snapshot: Literal["TALK", "CONNECT", "CIRCLE"] | None
    entitlement_cycle_started_at: datetime | None
    membership_tier_snapshot: Literal["SILVER", "COMPANION", "PRESTIGE"] | None
    registered_at: datetime
    cancelled_at: datetime | None


class MyEventRegistrationData(PaymentSchema):
    registration: EventRegistrationData
    event: EventData


class MyEventRegistrationListData(PaymentSchema):
    registrations: list[MyEventRegistrationData]


PRIVATE_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Event action is forbidden.", "model": ErrorEnvelope},
    404: {
        "description": "Event or registration was not found.",
        "model": ErrorEnvelope,
    },
    409: {"description": "Event state conflict.", "model": ErrorEnvelope},
    422: {"description": "Event request is invalid.", "model": ErrorEnvelope},
}


def _event_data(event: CommunityEvent) -> EventData:
    return EventData.model_validate(event)


def _registration_data(
    registration: CommunityEventRegistration,
) -> EventRegistrationData:
    return EventRegistrationData.model_validate(registration)


@router.get(
    "/events",
    response_model=PaginatedSuccessEnvelope[EventListData],
    responses={422: PRIVATE_RESPONSES[422]},
)
async def list_events(
    request: Request,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[EventListData]:
    events, total = await CommunityEventService(session).list_public(
        page=page, page_size=page_size
    )
    return PaginatedSuccessEnvelope(
        data=EventListData(events=[_event_data(event) for event in events]),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/events/me/registrations",
    response_model=PaginatedSuccessEnvelope[MyEventRegistrationListData],
    responses=PRIVATE_RESPONSES,
)
async def my_event_registrations(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[MyEventRegistrationListData]:
    rows, total = await CommunityEventService(session).my_registrations(
        principal, page=page, page_size=page_size
    )
    return PaginatedSuccessEnvelope(
        data=MyEventRegistrationListData(
            registrations=[
                MyEventRegistrationData(
                    registration=_registration_data(registration),
                    event=_event_data(event),
                )
                for registration, event in rows
            ]
        ),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/events/{event_id}/registrations",
    response_model=SuccessEnvelope[EventRegistrationData],
    status_code=201,
    responses={
        **PRIVATE_RESPONSES,
        402: {"description": "Ticket payment is required."},
    },
)
async def register_for_event(
    event_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EventRegistrationData]:
    registration = await CommunityEventService(session).register(principal, event_id)
    return SuccessEnvelope(
        data=_registration_data(registration),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/events/{event_id}/registrations/me",
    response_model=SuccessEnvelope[EventRegistrationData],
    responses=PRIVATE_RESPONSES,
)
async def cancel_event_registration(
    event_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EventRegistrationData]:
    registration = await CommunityEventService(session).cancel_registration(
        principal, event_id
    )
    return SuccessEnvelope(
        data=_registration_data(registration),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "",
    response_model=PaginatedSuccessEnvelope[EventListData],
    responses=PRIVATE_RESPONSES,
)
async def admin_list_events(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[EventListData]:
    events, total = await CommunityEventService(session).list_admin(
        principal, page=page, page_size=page_size
    )
    return PaginatedSuccessEnvelope(
        data=EventListData(events=[_event_data(event) for event in events]),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@admin_router.post(
    "",
    response_model=SuccessEnvelope[EventData],
    status_code=201,
    responses=PRIVATE_RESPONSES,
)
async def create_event(
    payload: EventCreateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EventData]:
    event = await CommunityEventService(session).create(
        principal, **payload.model_dump()
    )
    return SuccessEnvelope(
        data=_event_data(event),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.patch(
    "/{event_id}",
    response_model=SuccessEnvelope[EventData],
    responses=PRIVATE_RESPONSES,
)
async def update_event(
    event_id: UUID,
    payload: EventUpdateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EventData]:
    event = await CommunityEventService(session).update(
        principal, event_id, **payload.model_dump(exclude_unset=True)
    )
    return SuccessEnvelope(
        data=_event_data(event),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/{event_id}/publish",
    response_model=SuccessEnvelope[EventData],
    responses=PRIVATE_RESPONSES,
)
async def publish_event(
    event_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EventData]:
    event = await CommunityEventService(session).publish(principal, event_id)
    return SuccessEnvelope(
        data=_event_data(event),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/{event_id}/cancel",
    response_model=SuccessEnvelope[EventData],
    responses=PRIVATE_RESPONSES,
)
async def cancel_event(
    event_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[EventData]:
    event = await CommunityEventService(session).cancel_event(principal, event_id)
    return SuccessEnvelope(
        data=_event_data(event),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
