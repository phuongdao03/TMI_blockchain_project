from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)
from pydantic.alias_generators import to_camel

Money = Annotated[int, Field(ge=0, le=1_000_000_000_000, strict=True)]
ServiceCode = Literal[
    "DOSSIER_SUBMISSION", "DOSSIER_APPROVAL", "MEMBERSHIP", "ADVERTISING"
]


def _default_services() -> list[ServiceCode]:
    return ["DOSSIER_SUBMISSION"]


class PromotionSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class AudienceRule(PromotionSchema):
    mode: Literal["ALL", "ANY"] = "ALL"
    registered_before: AwareDatetime | None = None
    registered_after: AwareDatetime | None = None
    membership_tiers: list[Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"]] = (
        Field(default_factory=list, max_length=4)
    )
    user_ids: list[UUID] = Field(default_factory=list, max_length=50_000)
    purchase_history: Literal["ANY", "FIRST", "RETURNING"] = "ANY"


class Presentation(PromotionSchema):
    template: Literal["GIFT", "PREMIUM", "MINIMAL", "LIMITED"] = "GIFT"
    theme: Literal["CLASSIC", "LIGHT", "PREMIUM", "MINIMAL"] = "LIGHT"
    subtitle: str = Field(default="Món quà tri ân", max_length=200)
    primary_cta: str = Field(default="Nhận voucher ngay", min_length=1, max_length=80)
    secondary_cta: str = Field(default="Để sau", min_length=1, max_length=80)
    alt_text: str = Field(default="Voucher Tinh Hoa Việt", max_length=255)
    image_asset_id: UUID | None = None
    mobile_image_asset_id: UUID | None = None
    card_image_asset_id: UUID | None = None
    thumbnail_asset_id: UUID | None = None
    image_fit: Literal["contain", "cover"] = "contain"
    focal_x: int = Field(default=50, ge=0, le=100)
    focal_y: int = Field(default=50, ge=0, le=100)
    background_color: str = Field(default="#fff9ed", pattern=r"^#[0-9a-fA-F]{6}$")
    text_color: str = Field(default="#671b16", pattern=r"^#[0-9a-fA-F]{6}$")
    cta_color: str = Field(default="#9d0000", pattern=r"^#[0-9a-fA-F]{6}$")
    border_radius: int = Field(default=16, ge=0, le=32)
    overlay: float = Field(default=0.65, ge=0, le=0.8)
    trigger: Literal[
        "LOGIN", "DASHBOARD", "ISSUED", "CHECKOUT", "NOTIFICATION", "BANNER"
    ] = "LOGIN"
    frequency: Literal["ONCE", "SESSION", "LIMITED"] = "SESSION"
    max_views: int = Field(default=3, ge=1, le=100)
    cooldown_hours: int = Field(default=24, ge=0, le=8760)
    enabled: bool = True
    notify_in_app: bool = True


class PromotionPolicy(PromotionSchema):
    discount_type: Literal["FIXED", "PERCENT"] = "FIXED"
    percentage_bps: int = Field(default=0, ge=0, le=10000)
    discount_cap_vnd: Money | None = None
    minimum_order_vnd: Money = 0
    maximum_order_vnd: Money | None = None
    service_codes: list[ServiceCode] = Field(
        default_factory=_default_services, min_length=1, max_length=4
    )
    product_ids: list[UUID] = Field(default_factory=list, max_length=500)
    first_order_only: bool = False
    subsequent_order_only: bool = False
    stacking_policy: Literal["NONE", "BEST", "MEMBERSHIP_FIRST"] = "NONE"
    budget_vnd: Money | None = None
    issuance_limit: int | None = Field(default=None, ge=1, le=10_000_000)
    redemption_limit: int | None = Field(default=None, ge=1, le=10_000_000)
    uses_per_voucher: int = Field(default=1, ge=1, le=100)
    vouchers_per_user: int = Field(default=1, ge=1, le=100)
    daily_limit: int | None = Field(default=None, ge=1, le=1_000_000)
    user_discount_limit_vnd: Money | None = None
    fixed_expires_at: AwareDatetime | None = None
    allow_use_after_end: bool = True
    restore_on_refund: bool = False
    public_code: str | None = Field(
        default=None, min_length=3, max_length=64, pattern=r"^[A-Z0-9_-]+$"
    )
    audience: AudienceRule = Field(default_factory=AudienceRule)
    presentation: Presentation = Field(default_factory=Presentation)

    @model_validator(mode="after")
    def coherent(self) -> "PromotionPolicy":
        if self.first_order_only and self.subsequent_order_only:
            raise ValueError("First and subsequent order rules are mutually exclusive.")
        if self.discount_type == "PERCENT" and self.percentage_bps == 0:
            raise ValueError("Percentage discount must be positive.")
        if (
            self.maximum_order_vnd is not None
            and self.maximum_order_vnd < self.minimum_order_vnd
        ):
            raise ValueError("Maximum order must be at least the minimum.")
        return self


class CampaignInput(PromotionSchema):
    code: str = Field(min_length=3, max_length=64, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=255)
    internal_description: str = Field(default="", max_length=4000)
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(max_length=4000)
    terms: str = Field(min_length=2, max_length=4000)
    image_path: str = Field(
        default="/images/promotions/golden-voucher.png", max_length=512
    )
    amount_vnd: Annotated[int, Field(ge=1, le=1_000_000_000, strict=True)] = 200_000
    validity_days: int = Field(default=60, ge=1, le=3660)
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    program_type: Literal["AUTO", "CLAIM", "CODE", "MANUAL", "FIRST_ORDER"] = "CLAIM"
    policy: PromotionPolicy = Field(default_factory=PromotionPolicy)

    @model_validator(mode="after")
    def valid_period(self) -> "CampaignInput":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("Campaign end must follow its start.")
        if not self.image_path.startswith(
            ("/images/promotions/", "/api/v1/promotion-media/")
        ):
            raise ValueError("Select a library image or the built-in voucher asset.")
        if self.program_type == "FIRST_ORDER":
            if self.policy.subsequent_order_only:
                raise ValueError(
                    "First-order campaigns cannot require returning orders."
                )
            self.policy.first_order_only = True
        if self.program_type == "CODE" and not self.policy.public_code:
            raise ValueError("Code campaigns require a public code.")
        return self


class CampaignData(CampaignInput):
    id: UUID
    status: str
    policy_version: int
    created_at: datetime
    updated_at: datetime
    budget_reserved_vnd: int
    budget_spent_vnd: int


class VoucherOfferData(PromotionSchema):
    id: UUID
    title: str
    description: str
    terms: str
    image_path: str
    amount_vnd: int
    validity_days: int
    policy: PromotionPolicy = Field(default_factory=PromotionPolicy)
    claimed_voucher_id: UUID | None = None
    expires_at: datetime | None = None


class VoucherClaimData(PromotionSchema):
    id: UUID
    campaign_id: UUID
    title: str
    terms: str
    image_path: str
    amount_vnd: int
    claimed_at: datetime
    expires_at: datetime
    status: str = "AVAILABLE"
    unique_code: str | None = None
    valid_from: datetime | None = None
    redeemed_at: datetime | None = None
    uses_used: int = 0
    policy: PromotionPolicy = Field(default_factory=PromotionPolicy)

    @computed_field
    def expired(self) -> bool:
        value = self.expires_at
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value <= datetime.now(UTC)


class PresentationEvent(PromotionSchema):
    event: Literal["SEEN", "CLICKED", "DISMISSED", "OPT_OUT"]


class RedeemCodeInput(PromotionSchema):
    code: str = Field(min_length=3, max_length=64)
