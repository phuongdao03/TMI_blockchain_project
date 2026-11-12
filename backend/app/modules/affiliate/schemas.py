from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class AffiliateSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class AffiliateDashboardData(AffiliateSchema):
    referral_code: str
    referral_url: str
    status: str
    click_count: int
    attributed_user_count: int
    pending_commission_minor: int
    on_hold_commission_minor: int
    available_balance_minor: int
    reserved_balance_minor: int
    lifetime_earned_minor: int
    total_withdrawn_minor: int
    total_reversed_minor: int
    created_at: datetime


class ReferralClickRequest(AffiliateSchema):
    referral_code: Annotated[str, Field(min_length=8, max_length=32)]
    event_id: UUID


class ReferralClickData(AffiliateSchema):
    id: UUID
    created_at: datetime


class ReferralClaimRequest(AffiliateSchema):
    referral_code: Annotated[str, Field(min_length=8, max_length=32)]
    click_id: UUID | None = None


class ReferralAttributionData(AffiliateSchema):
    id: UUID
    affiliate_user_id: UUID
    referred_user_id: UUID
    referral_code_snapshot: str
    attributed_at: datetime
    expires_at: datetime


class AffiliateReferralSummaryData(AffiliateSchema):
    id: UUID
    attributed_at: datetime
    expires_at: datetime
    conversion_count: int
    revenue_minor: int
    commission_amount_minor: int


class AffiliateProfileAdminData(AffiliateSchema):
    user_id: UUID
    email: str
    referral_code: str
    status: str
    created_at: datetime
    click_count: int
    attributed_user_count: int


class AffiliateProfileStatusChangeData(AffiliateSchema):
    status: str
    reason: str
    actor_user_id: UUID | None
    created_at: datetime


class AffiliateProfileStatusRequest(AffiliateSchema):
    reason: Annotated[str, Field(min_length=10, max_length=500)]


class CommissionReviewRequest(AffiliateSchema):
    reason: Annotated[str, Field(min_length=10, max_length=1000)]


class CommissionRateInput(AffiliateSchema):
    service_code: Annotated[
        str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_]+$")
    ]
    direct_rate_basis_points: Annotated[int, Field(strict=True, ge=0, le=10_000)]


class CommissionRateData(AffiliateSchema):
    service_code: str
    direct_rate_basis_points: int


class CommissionRuleSetCreateRequest(AffiliateSchema):
    enabled: bool = False
    attribution_window_days: Annotated[int, Field(strict=True, ge=0, le=3650)] = 30
    hold_days: Annotated[int, Field(strict=True, ge=0, le=3650)] = 30
    level2_enabled: bool = False
    level2_rate_basis_points: Annotated[int, Field(strict=True, ge=0, le=10_000)] = 0
    rates: list[CommissionRateInput] = Field(default_factory=list, max_length=100)


class CommissionRuleSetData(AffiliateSchema):
    id: UUID
    version_no: int
    status: str
    enabled: bool
    attribution_window_days: int
    hold_days: int
    level2_enabled: bool
    level2_rate_basis_points: int
    effective_from: datetime | None
    published_at: datetime | None
    published_by_user_id: UUID | None
    rates: list[CommissionRateData]


class AffiliateCommissionData(AffiliateSchema):
    id: UUID
    affiliate_user_id: UUID
    referred_user_id: UUID
    rule_set_version: int
    service_code: str
    source_reference: str
    amount_minor: int
    commission_amount_minor: int
    rate_basis_points: int
    commission_level: int
    currency: str
    status: str
    earned_at: datetime
    hold_until: datetime
    approved_at: datetime | None
    reviewed_by_user_id: UUID | None
    review_reason: str | None
    reversed_at: datetime | None
    reversal_reason: str | None
    created_at: datetime
