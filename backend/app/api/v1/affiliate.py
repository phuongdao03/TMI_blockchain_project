from typing import Annotated, Literal
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

from app.core.errors import DomainError
from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.affiliate.dependencies import AffiliateServiceDependency
from app.modules.affiliate.schemas import (
    AffiliateCommissionData,
    AffiliateDashboardData,
    AffiliateProfileAdminData,
    AffiliateProfileStatusRequest,
    AffiliateReferralSummaryData,
    CommissionRateData,
    CommissionReviewRequest,
    CommissionRuleSetCreateRequest,
    CommissionRuleSetData,
    ReferralAttributionData,
    ReferralClaimRequest,
    ReferralClickData,
    ReferralClickRequest,
)
from app.modules.affiliate.service import CommissionRuleSetView
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SettingsDependency,
)
from app.modules.auth.session_service import AuthPrincipal

router = APIRouter(prefix="/api/v1/affiliate", tags=["affiliate"])
admin_router = APIRouter(prefix="/api/v1/admin/affiliate", tags=["admin affiliate"])
CommissionStatus = Literal[
    "PENDING", "ON_HOLD", "AVAILABLE", "REJECTED", "REVERSED", "SUPPRESSED"
]


def _require_rule_management(principal: AuthPrincipal) -> None:
    AuthorizationPolicy.require_capability(
        principal,
        PolicyRequirement(permission="affiliate.rules.manage"),
        lambda: DomainError(
            code="AFFILIATE_FORBIDDEN",
            message="Bạn không có quyền quản lý chính sách Affiliate.",
            status_code=403,
        ),
    )


def _require_commission_review(principal: AuthPrincipal) -> None:
    AuthorizationPolicy.require_capability(
        principal,
        PolicyRequirement(permission="affiliate.commissions.approve"),
        lambda: DomainError(
            code="AFFILIATE_FORBIDDEN",
            message="Bạn không có quyền xử lý hoa hồng Affiliate.",
            status_code=403,
        ),
    )


def _require_profile_management(principal: AuthPrincipal) -> None:
    AuthorizationPolicy.require_capability(
        principal,
        PolicyRequirement(permission="affiliate.profiles.manage"),
        lambda: DomainError(
            code="AFFILIATE_FORBIDDEN",
            message="Báº¡n khÃ´ng cÃ³ quyá»n quáº£n lÃ½ há»“ sÆ¡ Affiliate.",
            status_code=403,
        ),
    )


def _rule_data(view: CommissionRuleSetView) -> CommissionRuleSetData:
    rule_set = view.rule_set
    return CommissionRuleSetData(
        id=rule_set.id,
        version_no=rule_set.version_no,
        status=rule_set.status,
        enabled=rule_set.enabled,
        attribution_window_days=rule_set.attribution_window_days,
        hold_days=rule_set.hold_days,
        level2_enabled=rule_set.level2_enabled,
        level2_rate_basis_points=rule_set.level2_rate_basis_points,
        effective_from=rule_set.effective_from,
        published_at=rule_set.published_at,
        published_by_user_id=rule_set.published_by_user_id,
        rates=[
            CommissionRateData(
                service_code=rate.service_code,
                direct_rate_basis_points=rate.direct_rate_basis_points,
            )
            for rate in view.rates
        ],
    )


@router.get("/me", response_model=SuccessEnvelope[AffiliateDashboardData])
async def get_affiliate_dashboard(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    settings: SettingsDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[AffiliateDashboardData]:
    dashboard = await service.dashboard(principal.user_id)
    response.headers["Cache-Control"] = "no-store"
    code = dashboard.profile.referral_code
    referral_url = f"{settings.app_base_url.rstrip('/')}/?{urlencode({'ref': code})}"
    return SuccessEnvelope(
        data=AffiliateDashboardData(
            referral_code=code,
            referral_url=referral_url,
            status=dashboard.profile.status,
            click_count=dashboard.click_count,
            attributed_user_count=dashboard.attributed_user_count,
            pending_commission_minor=dashboard.pending_commission_minor,
            on_hold_commission_minor=dashboard.on_hold_commission_minor,
            available_balance_minor=dashboard.available_balance_minor,
            reserved_balance_minor=dashboard.reserved_balance_minor,
            lifetime_earned_minor=dashboard.lifetime_earned_minor,
            total_withdrawn_minor=dashboard.total_withdrawn_minor,
            total_reversed_minor=dashboard.total_reversed_minor,
            created_at=dashboard.profile.created_at,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/referral-clicks",
    response_model=SuccessEnvelope[ReferralClickData],
    status_code=status.HTTP_201_CREATED,
)
async def record_referral_click(
    request: Request,
    payload: ReferralClickRequest,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[ReferralClickData]:
    click = await service.record_click(
        referral_code=payload.referral_code,
        event_id=payload.event_id,
    )
    return SuccessEnvelope(
        data=ReferralClickData(id=click.id, created_at=click.created_at),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/referrals/claim",
    response_model=SuccessEnvelope[ReferralAttributionData],
)
async def claim_referral(
    request: Request,
    payload: ReferralClaimRequest,
    principal: CsrfProtectedPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[ReferralAttributionData]:
    attribution = await service.claim_referral(
        referred_user_id=principal.user_id,
        referral_code=payload.referral_code,
        click_id=payload.click_id,
    )
    return SuccessEnvelope(
        data=ReferralAttributionData.model_validate(attribution),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/me/commissions",
    response_model=SuccessEnvelope[list[AffiliateCommissionData]],
)
async def list_my_commissions(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    service: AffiliateServiceDependency,
    commission_status: Annotated[CommissionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SuccessEnvelope[list[AffiliateCommissionData]]:
    rows = await service.list_owned_commissions(
        user_id=principal.user_id,
        commission_status=commission_status,
        limit=limit,
    )
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=[AffiliateCommissionData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/me/referrals",
    response_model=SuccessEnvelope[list[AffiliateReferralSummaryData]],
)
async def list_my_referrals(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    service: AffiliateServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> SuccessEnvelope[list[AffiliateReferralSummaryData]]:
    rows = await service.list_owned_referrals(
        user_id=principal.user_id,
        limit=limit,
        offset=offset,
    )
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=[AffiliateReferralSummaryData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/profiles",
    response_model=SuccessEnvelope[list[AffiliateProfileAdminData]],
)
async def list_affiliate_profiles(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    service: AffiliateServiceDependency,
    search: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    profile_status: Annotated[
        Literal["ACTIVE", "SUSPENDED"] | None, Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> SuccessEnvelope[list[AffiliateProfileAdminData]]:
    _require_profile_management(principal)
    rows = await service.list_profiles(
        search=search,
        profile_status=profile_status,
        limit=limit,
        offset=offset,
    )
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=[AffiliateProfileAdminData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/profiles/{user_id}",
    response_model=SuccessEnvelope[AffiliateProfileAdminData],
)
async def get_affiliate_profile(
    request: Request,
    response: Response,
    user_id: UUID,
    principal: CurrentPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[AffiliateProfileAdminData]:
    _require_profile_management(principal)
    row = await service.get_profile_admin_detail(user_id)
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=AffiliateProfileAdminData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/profiles/{user_id}/referrals",
    response_model=SuccessEnvelope[list[AffiliateReferralSummaryData]],
)
async def list_affiliate_profile_referrals(
    request: Request,
    response: Response,
    user_id: UUID,
    principal: CurrentPrincipalDependency,
    service: AffiliateServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> SuccessEnvelope[list[AffiliateReferralSummaryData]]:
    _require_profile_management(principal)
    rows = await service.list_owned_referrals(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=[AffiliateReferralSummaryData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/profiles/{user_id}/suspend",
    response_model=SuccessEnvelope[AffiliateProfileAdminData],
)
async def suspend_affiliate_profile(
    request: Request,
    response: Response,
    user_id: UUID,
    payload: AffiliateProfileStatusRequest,
    principal: CsrfProtectedPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[AffiliateProfileAdminData]:
    _require_profile_management(principal)
    row = await service.set_profile_status(
        user_id=user_id,
        actor_user_id=principal.user_id,
        profile_status="SUSPENDED",
        reason=payload.reason,
    )
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=AffiliateProfileAdminData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/profiles/{user_id}/restore",
    response_model=SuccessEnvelope[AffiliateProfileAdminData],
)
async def restore_affiliate_profile(
    request: Request,
    response: Response,
    user_id: UUID,
    payload: AffiliateProfileStatusRequest,
    principal: CsrfProtectedPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[AffiliateProfileAdminData]:
    _require_profile_management(principal)
    row = await service.set_profile_status(
        user_id=user_id,
        actor_user_id=principal.user_id,
        profile_status="ACTIVE",
        reason=payload.reason,
    )
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=AffiliateProfileAdminData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/commission-rules",
    response_model=SuccessEnvelope[list[CommissionRuleSetData]],
)
async def list_commission_rules(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[list[CommissionRuleSetData]]:
    _require_rule_management(principal)
    rows = await service.list_rule_sets()
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=[_rule_data(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/commission-rules",
    response_model=SuccessEnvelope[CommissionRuleSetData],
    status_code=status.HTTP_201_CREATED,
)
async def create_commission_rules(
    request: Request,
    payload: CommissionRuleSetCreateRequest,
    principal: CsrfProtectedPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[CommissionRuleSetData]:
    _require_rule_management(principal)
    view = await service.create_rule_set(
        actor_user_id=principal.user_id,
        enabled=payload.enabled,
        attribution_window_days=payload.attribution_window_days,
        hold_days=payload.hold_days,
        rates=tuple(
            (rate.service_code.upper(), rate.direct_rate_basis_points)
            for rate in payload.rates
        ),
    )
    return SuccessEnvelope(
        data=_rule_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/commission-rules/{rule_set_id}/publish",
    response_model=SuccessEnvelope[CommissionRuleSetData],
)
async def publish_commission_rules(
    request: Request,
    rule_set_id: UUID,
    principal: CsrfProtectedPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[CommissionRuleSetData]:
    _require_rule_management(principal)
    view = await service.publish_rule_set(
        actor_user_id=principal.user_id,
        rule_set_id=rule_set_id,
    )
    return SuccessEnvelope(
        data=_rule_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/commissions",
    response_model=SuccessEnvelope[list[AffiliateCommissionData]],
)
async def list_admin_commissions(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    service: AffiliateServiceDependency,
    commission_status: Annotated[CommissionStatus | None, Query(alias="status")] = None,
    affiliate_user_id: Annotated[UUID | None, Query(alias="affiliateUserId")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SuccessEnvelope[list[AffiliateCommissionData]]:
    _require_commission_review(principal)
    rows = await service.list_commissions(
        affiliate_user_id=affiliate_user_id,
        commission_status=commission_status,
        limit=limit,
    )
    response.headers["Cache-Control"] = "no-store"
    return SuccessEnvelope(
        data=[AffiliateCommissionData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/commissions/{commission_id}/approve",
    response_model=SuccessEnvelope[AffiliateCommissionData],
)
async def approve_commission(
    request: Request,
    commission_id: UUID,
    principal: CsrfProtectedPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[AffiliateCommissionData]:
    _require_commission_review(principal)
    commission = await service.approve_commission(
        commission_id=commission_id,
        actor_user_id=principal.user_id,
    )
    return SuccessEnvelope(
        data=AffiliateCommissionData.model_validate(commission),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/commissions/{commission_id}/reject",
    response_model=SuccessEnvelope[AffiliateCommissionData],
)
async def reject_commission(
    request: Request,
    commission_id: UUID,
    payload: CommissionReviewRequest,
    principal: CsrfProtectedPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[AffiliateCommissionData]:
    _require_commission_review(principal)
    commission = await service.reject_commission(
        commission_id=commission_id,
        actor_user_id=principal.user_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=AffiliateCommissionData.model_validate(commission),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/commissions/{commission_id}/reverse",
    response_model=SuccessEnvelope[AffiliateCommissionData],
)
async def reverse_commission(
    request: Request,
    commission_id: UUID,
    payload: CommissionReviewRequest,
    principal: CsrfProtectedPrincipalDependency,
    service: AffiliateServiceDependency,
) -> SuccessEnvelope[AffiliateCommissionData]:
    _require_commission_review(principal)
    commission = await service.reverse_commission(
        commission_id=commission_id,
        actor_user_id=principal.user_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=AffiliateCommissionData.model_validate(commission),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
