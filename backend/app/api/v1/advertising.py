from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core.errors import DomainError
from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.advertising.admin import AdvertisingAdminService
from app.modules.advertising.delivery import AdvertisingDeliveryService
from app.modules.advertising.inventory import AdvertisingInventoryService
from app.modules.advertising.models import AdvertisingCreative, AdvertisingOrder
from app.modules.advertising.schemas import (
    AdminPlacementInventoryData,
    AdvertisingSchema,
    AvailabilityData,
    CampaignData,
    CampaignMetricsData,
    CampaignReviewData,
    CampaignSummaryData,
    CreateCampaignRequest,
    CreatePackageRequest,
    CreatePlacementRequest,
    CreateReservationRequest,
    CreativeData,
    DeliveryData,
    DiscountPolicyData,
    JoinWaitlistRequest,
    OrderData,
    PackageData,
    PauseCampaignRequest,
    PlacementData,
    PlacementReportData,
    QuoteData,
    QuoteRequest,
    RenewalQuoteData,
    RescheduleCampaignRequest,
    ReservationCheckoutData,
    ReservationData,
    ReviewDecisionRequest,
    TrackEventData,
    UpdateCreativeRequest,
    UpdateDiscountPolicyRequest,
    UpdatePackageRequest,
    UpdatePlacementRequest,
    WaitlistData,
)
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)

router = APIRouter(prefix="/api/v1", tags=["advertising"])


class CampaignCreatedData(AdvertisingSchema):
    campaign: CampaignData
    creative_id: UUID


def _require_admin(principal: CsrfProtectedPrincipalDependency) -> None:
    if "SUPER_ADMIN" not in principal.roles:
        raise DomainError(
            code="ADVERTISING_FORBIDDEN",
            message="Only a system administrator can manage advertising.",
            status_code=403,
        )


@router.get(
    "/advertising/placements",
    response_model=SuccessEnvelope[list[PlacementData]],
)
async def list_placements(
    request: Request, session: SessionDependency
) -> SuccessEnvelope[list[PlacementData]]:
    rows = await AdvertisingInventoryService(session).list_placements()
    return SuccessEnvelope(
        data=[PlacementData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/advertising/campaigns",
    response_model=SuccessEnvelope[list[CampaignReviewData]],
)
async def list_campaign_review_queue(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> SuccessEnvelope[list[CampaignReviewData]]:
    _require_admin(principal)
    rows = await AdvertisingAdminService(session).campaign_review_queue(
        principal, limit=limit
    )
    return SuccessEnvelope(
        data=[CampaignReviewData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/advertising/campaigns",
    response_model=SuccessEnvelope[list[CampaignSummaryData]],
)
async def list_campaigns(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[CampaignSummaryData]]:
    rows = await AdvertisingInventoryService(session).list_campaigns(principal)
    return SuccessEnvelope(
        data=[CampaignSummaryData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/advertising/packages",
    response_model=SuccessEnvelope[list[PackageData]],
)
async def list_packages(
    request: Request,
    session: SessionDependency,
    placement_code: Annotated[str | None, Query(alias="placementCode")] = None,
) -> SuccessEnvelope[list[PackageData]]:
    rows = await AdvertisingInventoryService(session).list_packages(
        placement_code=placement_code
    )
    return SuccessEnvelope(
        data=[PackageData.model_validate(package) for package, _ in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/advertising/availability",
    response_model=SuccessEnvelope[AvailabilityData],
)
async def get_availability(
    request: Request,
    session: SessionDependency,
    placement_code: Annotated[str, Query(alias="placementCode")],
    package_code: Annotated[str, Query(alias="packageCode")],
    start_at: Annotated[datetime, Query(alias="startAt")],
    search_days: Annotated[int, Query(alias="searchDays", ge=1, le=90)] = 30,
) -> SuccessEnvelope[AvailabilityData]:
    result = await AdvertisingInventoryService(session).availability(
        placement_code=placement_code,
        package_code=package_code,
        start_at=start_at,
        search_days=search_days,
    )
    return SuccessEnvelope(
        data=AvailabilityData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/advertising/quotes", response_model=SuccessEnvelope[QuoteData])
async def create_quote(
    payload: QuoteRequest,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[QuoteData]:
    result = await AdvertisingInventoryService(session).quote(
        principal, package_code=payload.package_code
    )
    return SuccessEnvelope(
        data=QuoteData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/advertising/campaigns",
    status_code=201,
    response_model=SuccessEnvelope[CampaignCreatedData],
)
async def create_campaign(
    payload: CreateCampaignRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CampaignCreatedData]:
    service = AdvertisingInventoryService(session)
    campaign = await service.create_campaign(
        principal,
        dossier_id=payload.dossier_id,
        package_code=payload.package_code,
        title=payload.title,
        description=payload.description,
        image_url=str(payload.image_url) if payload.image_url else None,
        destination_url=payload.destination_url,
    )
    creative = await session.scalar(
        select(AdvertisingCreative)
        .where(AdvertisingCreative.campaign_id == campaign.id)
        .order_by(AdvertisingCreative.version.desc())
        .limit(1)
    )
    assert creative is not None
    return SuccessEnvelope(
        data=CampaignCreatedData(
            campaign=CampaignData.model_validate(campaign), creative_id=creative.id
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/advertising/campaigns/{campaign_id}/creative",
    response_model=SuccessEnvelope[CreativeData],
)
async def update_campaign_creative(
    campaign_id: UUID,
    payload: UpdateCreativeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CreativeData]:
    result = await AdvertisingInventoryService(session).update_campaign_creative(
        principal,
        campaign_id,
        title=payload.title,
        description=payload.description,
        image_url=str(payload.image_url) if payload.image_url else None,
        destination_url=payload.destination_url,
    )
    return SuccessEnvelope(
        data=CreativeData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/advertising/campaigns/{campaign_id}/submit-review",
    response_model=SuccessEnvelope[CampaignData],
)
async def submit_campaign(
    campaign_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CampaignData]:
    result = await AdvertisingInventoryService(session).submit_campaign(
        principal, campaign_id
    )
    return SuccessEnvelope(
        data=CampaignData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/advertising/reservations",
    status_code=201,
    response_model=SuccessEnvelope[ReservationCheckoutData],
)
async def create_reservation(
    payload: CreateReservationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> SuccessEnvelope[ReservationCheckoutData]:
    result = await AdvertisingInventoryService(session).reserve(
        principal,
        campaign_id=payload.campaign_id,
        start_at=payload.start_at,
        idempotency_key=idempotency_key,
    )
    order = await session.scalar(
        select(AdvertisingOrder).where(
            AdvertisingOrder.reservation_id == result.id,
            AdvertisingOrder.user_id == principal.user_id,
        )
    )
    assert order is not None
    return SuccessEnvelope(
        data=ReservationCheckoutData(
            reservation=ReservationData.model_validate(result),
            order=OrderData.model_validate(order),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/advertising/reservations/{reservation_id}",
    response_model=SuccessEnvelope[ReservationCheckoutData],
)
async def get_reservation(
    reservation_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[ReservationCheckoutData]:
    result = await AdvertisingInventoryService(session).get_reservation(
        principal, reservation_id
    )
    order = await session.scalar(
        select(AdvertisingOrder).where(
            AdvertisingOrder.reservation_id == result.id,
            AdvertisingOrder.user_id == principal.user_id,
        )
    )
    assert order is not None
    return SuccessEnvelope(
        data=ReservationCheckoutData(
            reservation=ReservationData.model_validate(result),
            order=OrderData.model_validate(order),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/advertising/waitlist",
    response_model=SuccessEnvelope[list[WaitlistData]],
)
async def list_waitlist(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[WaitlistData]]:
    rows = await AdvertisingInventoryService(session).list_waitlist(principal)
    return SuccessEnvelope(
        data=[WaitlistData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/advertising/waitlist",
    status_code=201,
    response_model=SuccessEnvelope[WaitlistData],
)
async def join_waitlist(
    payload: JoinWaitlistRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[WaitlistData]:
    result = await AdvertisingInventoryService(session).join_waitlist(
        principal,
        campaign_id=payload.campaign_id,
        start_at=payload.start_at,
    )
    return SuccessEnvelope(
        data=WaitlistData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/advertising/waitlist/{entry_id}",
    response_model=SuccessEnvelope[WaitlistData],
)
async def cancel_waitlist(
    entry_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[WaitlistData]:
    result = await AdvertisingInventoryService(session).cancel_waitlist(
        principal, entry_id
    )
    return SuccessEnvelope(
        data=WaitlistData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/advertising/campaigns/{campaign_id}/review",
    response_model=SuccessEnvelope[CampaignData],
)
async def review_campaign(
    campaign_id: UUID,
    payload: ReviewDecisionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CampaignData]:
    _require_admin(principal)
    if payload.decision is None and payload.approve is None:
        raise DomainError(
            code="ADVERTISING_INVALID_REVIEW_DECISION",
            message="Provide a moderation decision.",
            status_code=422,
        )
    if payload.decision is not None and payload.approve is not None:
        decision_approve = payload.decision == "APPROVE"
        if decision_approve != payload.approve:
            raise DomainError(
                code="ADVERTISING_INVALID_REVIEW_DECISION",
                message="The moderation fields disagree.",
                status_code=422,
            )
    result = await AdvertisingInventoryService(session).review_campaign(
        principal,
        campaign_id,
        approve=payload.approve,
        decision=payload.decision,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=CampaignData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/advertising/campaigns/{campaign_id}/pause",
    response_model=SuccessEnvelope[CampaignData],
)
async def pause_campaign(
    campaign_id: UUID,
    payload: PauseCampaignRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CampaignData]:
    _require_admin(principal)
    result = await AdvertisingInventoryService(session).pause_campaign(
        principal, campaign_id, reason=payload.reason
    )
    return SuccessEnvelope(
        data=CampaignData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/advertising/placements",
    status_code=201,
    response_model=SuccessEnvelope[PlacementData],
)
async def create_placement(
    payload: CreatePlacementRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PlacementData]:
    _require_admin(principal)
    result = await AdvertisingInventoryService(session).create_placement(
        principal,
        code=payload.code,
        name=payload.name,
        page_location=payload.page_location,
        delivery_mode=payload.delivery_mode,
        capacity=payload.capacity,
        timezone=payload.timezone,
    )
    return SuccessEnvelope(
        data=PlacementData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/advertising/packages",
    status_code=201,
    response_model=SuccessEnvelope[PackageData],
)
async def create_package(
    payload: CreatePackageRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PackageData]:
    _require_admin(principal)
    result = await AdvertisingInventoryService(session).create_package(
        principal,
        code=payload.code,
        name=payload.name,
        placement_id=payload.placement_id,
        duration_hours=payload.duration_hours,
        rotation_weight=payload.rotation_weight,
        base_price_vnd=payload.base_price_vnd,
        active=payload.active,
        terms=payload.terms,
    )
    return SuccessEnvelope(
        data=PackageData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/admin/advertising/placements/{placement_id}",
    response_model=SuccessEnvelope[PlacementData],
)
async def update_placement(
    placement_id: UUID,
    payload: UpdatePlacementRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PlacementData]:
    _require_admin(principal)
    result = await AdvertisingInventoryService(session).update_placement(
        principal,
        placement_id,
        name=payload.name,
        page_location=payload.page_location,
        delivery_mode=payload.delivery_mode,
        capacity=payload.capacity,
        enabled=payload.enabled,
    )
    return SuccessEnvelope(
        data=PlacementData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/admin/advertising/packages/{package_id}",
    response_model=SuccessEnvelope[PackageData],
)
async def update_package(
    package_id: UUID,
    payload: UpdatePackageRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PackageData]:
    _require_admin(principal)
    result = await AdvertisingInventoryService(session).update_package(
        principal,
        package_id,
        name=payload.name,
        duration_hours=payload.duration_hours,
        rotation_weight=payload.rotation_weight,
        base_price_vnd=payload.base_price_vnd,
        terms=payload.terms,
        active=payload.active,
    )
    return SuccessEnvelope(
        data=PackageData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/advertising/orders/{order_id}", response_model=SuccessEnvelope[OrderData])
async def get_order(
    order_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[OrderData]:
    result = await AdvertisingInventoryService(session).get_order(principal, order_id)
    return SuccessEnvelope(
        data=OrderData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/advertising/orders/{order_id}/pay",
    response_model=SuccessEnvelope[OrderData],
)
async def pay_order(
    order_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> SuccessEnvelope[OrderData]:
    result = await AdvertisingInventoryService(session).pay_order(
        principal, order_id, idempotency_key=idempotency_key
    )
    return SuccessEnvelope(
        data=OrderData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/admin/advertising/membership-discounts/{tier}",
    response_model=SuccessEnvelope[DiscountPolicyData],
)
async def update_discount_policy(
    tier: str,
    payload: UpdateDiscountPolicyRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[DiscountPolicyData]:
    _require_admin(principal)
    result = await AdvertisingInventoryService(session).update_discount_policy(
        principal,
        tier,
        rate_basis_points=payload.rate_basis_points,
        annual_allowance_vnd=payload.annual_allowance_vnd,
        active=payload.active,
    )
    return SuccessEnvelope(
        data=DiscountPolicyData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/advertising/placements/{placement_code}/ad",
    response_model=SuccessEnvelope[DeliveryData | None],
)
async def select_ad(
    placement_code: str,
    request: Request,
    response: Response,
    session: SessionDependency,
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> SuccessEnvelope[DeliveryData | None]:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    result = await AdvertisingDeliveryService(session).select_ad(
        placement_code, user_agent=user_agent
    )
    return SuccessEnvelope(
        data=DeliveryData.model_validate(result) if result is not None else None,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/advertising/delivery/{event_id}/impression",
    response_model=SuccessEnvelope[TrackEventData],
)
async def record_ad_impression(
    event_id: UUID,
    request: Request,
    session: SessionDependency,
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> SuccessEnvelope[TrackEventData]:
    accepted = await AdvertisingDeliveryService(session).record_impression(
        event_id, user_agent=user_agent
    )
    return SuccessEnvelope(
        data=TrackEventData(accepted=accepted),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/advertising/delivery/{event_id}/click")
async def record_ad_click(
    event_id: UUID,
    session: SessionDependency,
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> RedirectResponse:
    destination = await AdvertisingDeliveryService(session).record_click(
        event_id, user_agent=user_agent
    )
    if destination is None:
        raise DomainError(
            code="ADVERTISING_DELIVERY_NOT_FOUND",
            message="This ad link is no longer available.",
            status_code=404,
        )
    return RedirectResponse(
        destination,
        status_code=303,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "strict-origin"},
    )


@router.get(
    "/advertising/campaigns/{campaign_id}/metrics",
    response_model=SuccessEnvelope[CampaignMetricsData],
)
async def get_campaign_metrics(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CampaignMetricsData]:
    result = await AdvertisingDeliveryService(session).campaign_metrics(
        principal, campaign_id
    )
    return SuccessEnvelope(
        data=CampaignMetricsData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/advertising/campaigns/{campaign_id}/renewal-quote",
    response_model=SuccessEnvelope[RenewalQuoteData],
)
async def create_renewal_quote(
    campaign_id: UUID,
    payload: RescheduleCampaignRequest,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[RenewalQuoteData]:
    result = await AdvertisingInventoryService(session).renewal_quote(
        principal,
        campaign_id,
        start_at=payload.start_at,
    )
    return SuccessEnvelope(
        data=RenewalQuoteData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/advertising/campaigns/{campaign_id}/reschedule",
    response_model=SuccessEnvelope[CampaignData],
)
async def reschedule_campaign(
    campaign_id: UUID,
    payload: RescheduleCampaignRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CampaignData]:
    result = await AdvertisingDeliveryService(session).reschedule_campaign(
        principal, campaign_id, start_at=payload.start_at
    )
    return SuccessEnvelope(
        data=CampaignData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/advertising/inventory",
    response_model=SuccessEnvelope[list[AdminPlacementInventoryData]],
)
async def get_admin_inventory(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    start_at: Annotated[datetime | None, Query(alias="startAt")] = None,
    end_at: Annotated[datetime | None, Query(alias="endAt")] = None,
) -> SuccessEnvelope[list[AdminPlacementInventoryData]]:
    _require_admin(principal)
    now = datetime.now(UTC)
    start = start_at or now
    end = end_at or start + timedelta(days=30)
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise DomainError(
            code="ADVERTISING_INVALID_INTERVAL",
            message="Inventory dates must be timezone aware and start before end.",
            status_code=422,
        )
    if end - start > timedelta(days=366):
        raise DomainError(
            code="ADVERTISING_INVALID_INTERVAL",
            message="Inventory date range cannot exceed one year.",
            status_code=422,
        )
    rows = await AdvertisingAdminService(session).inventory(
        principal, start_at=start, end_at=end
    )
    return SuccessEnvelope(
        data=[AdminPlacementInventoryData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/advertising/reports",
    response_model=SuccessEnvelope[list[PlacementReportData]],
)
async def get_admin_reports(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    start_date: Annotated[date | None, Query(alias="startDate")] = None,
    end_date: Annotated[date | None, Query(alias="endDate")] = None,
) -> SuccessEnvelope[list[PlacementReportData]]:
    _require_admin(principal)
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    end = end_date or tomorrow
    start = start_date or end - timedelta(days=30)
    if start >= end or end - start > timedelta(days=366):
        raise DomainError(
            code="ADVERTISING_INVALID_REPORT_RANGE",
            message="Report range must be positive and no longer than one year.",
            status_code=422,
        )
    rows = await AdvertisingAdminService(session).reports(
        principal, start_date=start, end_date=end
    )
    return SuccessEnvelope(
        data=[PlacementReportData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )
