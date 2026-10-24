from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class AdvertisingSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
    )


class PlacementData(AdvertisingSchema):
    id: UUID
    code: str
    name: str
    page_location: str
    delivery_mode: str
    capacity: int
    enabled: bool
    timezone: str


class PackageData(AdvertisingSchema):
    id: UUID
    code: str
    name: str
    placement_id: UUID
    duration_hours: int
    rotation_weight: int
    base_price_vnd: int
    price_version: int
    active: bool
    terms: str


class CreateCampaignRequest(AdvertisingSchema):
    dossier_id: UUID
    package_code: Annotated[str, Field(min_length=2, max_length=64)]
    title: Annotated[str, Field(min_length=2, max_length=120)]
    description: Annotated[str, Field(max_length=500)] = ""
    image_url: Annotated[AnyHttpUrl | None, Field(max_length=2048)] = None
    destination_url: Annotated[str, Field(min_length=1, max_length=2048)]

    @field_validator("destination_url")
    @classmethod
    def validate_destination_url(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Destination URL is required.")
        return clean


class UpdateCreativeRequest(AdvertisingSchema):
    title: Annotated[str, Field(min_length=2, max_length=120)]
    description: Annotated[str, Field(max_length=500)] = ""
    image_url: Annotated[AnyHttpUrl | None, Field(max_length=2048)] = None
    destination_url: Annotated[str, Field(min_length=1, max_length=2048)]

    @field_validator("destination_url")
    @classmethod
    def validate_destination_url(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Destination URL is required.")
        return clean


class CreativeData(AdvertisingSchema):
    id: UUID
    campaign_id: UUID
    version: int
    title: str
    description: str
    image_url: str | None
    destination_url: str
    review_status: str
    review_note: str | None


class CampaignReviewData(AdvertisingSchema):
    campaign_id: UUID
    owner_email: str
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    placement_code: str
    package_name: str
    campaign_status: str
    creative_id: UUID
    creative_version: int
    title: str
    description: str
    image_url: str | None
    destination_url: str
    review_status: str


class CampaignData(AdvertisingSchema):
    id: UUID
    dossier_id: UUID
    package_id: UUID
    placement_id: UUID
    purchase_context: str
    status: str
    desired_start_at: datetime | None
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    delivery_count: int
    created_at: datetime


class CampaignSummaryData(AdvertisingSchema):
    id: UUID
    dossier_id: UUID
    package_id: UUID
    placement_id: UUID
    placement_code: str
    placement_name: str
    purchase_context: str
    status: str
    desired_start_at: datetime | None
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    booking_start_at: datetime | None
    booking_end_at: datetime | None
    creative_title: str | None
    creative_description: str | None = None
    image_url: str | None
    destination_url: str | None = None
    creative_review_status: str | None
    creative_review_note: str | None
    payment_status: str | None
    delivery_count: int
    created_at: datetime


class DeliveryData(AdvertisingSchema):
    event_id: UUID
    placement_code: str
    title: str
    description: str
    image_url: str | None
    click_url: str


class TrackEventData(AdvertisingSchema):
    accepted: bool


class CampaignMetricsData(AdvertisingSchema):
    campaign_id: UUID
    delivery_count: int
    valid_impressions: int
    valid_clicks: int
    ctr_basis_points: int
    actual_share_basis_points: int
    target_share_basis_points: int
    active_seconds: int


class AdminInventoryItemData(AdvertisingSchema):
    id: UUID
    campaign_id: UUID
    owner_email: str
    dossier_code: str
    dossier_title: str
    status: str
    payment_status: str | None
    start_at: datetime
    end_at: datetime
    expires_at: datetime | None


class AdminPlacementInventoryData(AdvertisingSchema):
    id: UUID
    code: str
    name: str
    page_location: str
    delivery_mode: str
    capacity: int
    enabled: bool
    bookings: list[AdminInventoryItemData]
    reservations: list[AdminInventoryItemData]


class CampaignDistributionData(AdvertisingSchema):
    campaign_id: UUID
    title: str | None
    delivery_count: int
    valid_impressions: int
    valid_clicks: int
    target_share_basis_points: int
    actual_share_basis_points: int


class PlacementReportData(AdvertisingSchema):
    placement_id: UUID
    placement_code: str
    placement_name: str
    paid_orders: int
    paid_revenue_vnd: int
    delivery_count: int
    valid_impressions: int
    valid_clicks: int
    ctr_basis_points: int
    campaigns: list[CampaignDistributionData]


class RescheduleCampaignRequest(AdvertisingSchema):
    start_at: datetime

    @field_validator("start_at")
    @classmethod
    def require_aware_start(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("startAt must include a timezone.")
        return value


class AvailabilityRequest(AdvertisingSchema):
    placement_code: Annotated[str, Field(min_length=2, max_length=64)]
    package_code: Annotated[str, Field(min_length=2, max_length=64)]
    start_at: datetime
    search_days: Annotated[int, Field(ge=1, le=90)] = 30

    @field_validator("start_at")
    @classmethod
    def require_aware_start(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("startAt must include a timezone.")
        return value


class AvailabilityData(AdvertisingSchema):
    placement: PlacementData
    package: PackageData
    start_at: datetime
    end_at: datetime
    available: bool
    remaining_slots: int
    alternatives: list[datetime]


class CreateReservationRequest(AdvertisingSchema):
    campaign_id: UUID
    start_at: datetime

    @field_validator("start_at")
    @classmethod
    def require_aware_start(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("startAt must include a timezone.")
        return value


class JoinWaitlistRequest(AdvertisingSchema):
    campaign_id: UUID
    start_at: datetime

    @field_validator("start_at")
    @classmethod
    def require_aware_start(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("startAt must include a timezone.")
        return value


class ReservationData(AdvertisingSchema):
    id: UUID
    campaign_id: UUID
    placement_id: UUID
    start_at: datetime
    end_at: datetime
    expires_at: datetime
    status: str


class QuoteRequest(AdvertisingSchema):
    package_code: Annotated[str, Field(min_length=2, max_length=64)]


class QuoteData(AdvertisingSchema):
    placement_code: str
    placement_name: str
    package_code: str
    package_name: str
    duration_hours: int
    price_version: int
    membership_tier: str
    membership_cycle_start: datetime | None
    discount_policy_version: int
    discount_rate_basis_points: int
    remaining_discount_allowance_vnd: int
    base_amount_vnd: int
    discount_amount_vnd: int
    payable_amount_vnd: int


class RenewalQuoteData(AdvertisingSchema):
    quote: QuoteData
    availability: AvailabilityData


class OrderData(AdvertisingSchema):
    id: UUID
    reservation_id: UUID
    campaign_id: UUID
    membership_tier: str
    membership_cycle_start: datetime | None
    price_version: int
    discount_policy_version: int
    base_amount_vnd: int
    discount_amount_vnd: int
    payable_amount_vnd: int
    payment_status: str
    allowance_expires_at: datetime
    wallet_transaction_id: UUID | None
    pricing_snapshot: dict[str, object]
    paid_at: datetime | None


class ReservationCheckoutData(AdvertisingSchema):
    reservation: ReservationData
    order: OrderData


class WaitlistData(AdvertisingSchema):
    id: UUID
    campaign_id: UUID
    placement_id: UUID
    start_at: datetime
    end_at: datetime
    status: str
    created_at: datetime


class DiscountPolicyData(AdvertisingSchema):
    tier: str
    rate_basis_points: int
    annual_allowance_vnd: int
    policy_version: int
    active: bool


class ReviewDecisionRequest(AdvertisingSchema):
    approve: bool | None = None
    decision: Literal["APPROVE", "REJECT", "CHANGES_REQUESTED"] | None = None
    reason: Annotated[str | None, Field(max_length=1000)] = None


class PauseCampaignRequest(AdvertisingSchema):
    reason: Annotated[str, Field(min_length=3, max_length=1000)]


class UpdatePlacementRequest(AdvertisingSchema):
    name: Annotated[str | None, Field(min_length=1, max_length=160)] = None
    page_location: Annotated[str | None, Field(min_length=1, max_length=160)] = None
    delivery_mode: (
        Literal["EQUAL_ROTATION", "WEIGHTED_ROTATION", "EXCLUSIVE"] | None
    ) = None
    capacity: Annotated[int | None, Field(strict=True, ge=1, le=100)] = None
    enabled: bool | None = None


class CreatePlacementRequest(AdvertisingSchema):
    code: Annotated[str, Field(min_length=2, max_length=64)]
    name: Annotated[str, Field(min_length=1, max_length=160)]
    page_location: Annotated[str, Field(min_length=1, max_length=160)]
    delivery_mode: Literal["EQUAL_ROTATION", "WEIGHTED_ROTATION", "EXCLUSIVE"]
    capacity: Annotated[int, Field(strict=True, ge=1, le=100)]
    timezone: Annotated[str, Field(min_length=1, max_length=64)] = "Asia/Bangkok"


class CreatePackageRequest(AdvertisingSchema):
    code: Annotated[str, Field(min_length=2, max_length=64)]
    name: Annotated[str, Field(min_length=1, max_length=160)]
    placement_id: UUID
    duration_hours: Annotated[int, Field(strict=True, ge=1, le=8760)]
    rotation_weight: Annotated[int, Field(strict=True, ge=1, le=100)] = 1
    base_price_vnd: Annotated[int, Field(strict=True, ge=0, le=10_000_000_000)]
    active: bool = True
    terms: Annotated[str, Field(max_length=2000)] = ""


class UpdatePackageRequest(AdvertisingSchema):
    name: Annotated[str | None, Field(min_length=1, max_length=160)] = None
    duration_hours: Annotated[int | None, Field(strict=True, ge=1, le=8760)] = None
    rotation_weight: Annotated[int | None, Field(strict=True, ge=1, le=100)] = None
    base_price_vnd: Annotated[
        int | None, Field(strict=True, ge=0, le=10_000_000_000)
    ] = None
    terms: Annotated[str | None, Field(max_length=2000)] = None
    active: bool | None = None


class UpdateDiscountPolicyRequest(AdvertisingSchema):
    rate_basis_points: Annotated[int, Field(strict=True, ge=0, le=10_000)]
    annual_allowance_vnd: Annotated[int, Field(strict=True, ge=0, le=10_000_000_000)]
    active: bool = True
