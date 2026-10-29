from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.promotions.schemas import PromotionSchema, ServiceCode


class CheckoutVoucherRequest(PromotionSchema):
    service_code: ServiceCode
    resource_id: UUID
    renewal_opt_in: bool = False


class ApplyVoucherRequest(PromotionSchema):
    voucher_id: UUID | None


class CheckoutVoucherOption(PromotionSchema):
    voucher_id: UUID
    title: str
    discount_vnd: int
    payable_vnd: int
    expires_at: datetime


class CheckoutVoucherQuote(PromotionSchema):
    original_vnd: int
    membership_discount_vnd: int = 0
    vouchers: list[CheckoutVoucherOption] = Field(default_factory=list)
    recommended_voucher_id: UUID | None = None
    selected_voucher_id: UUID | None = None
    current_payable_vnd: int | None = None


class AppliedVoucherData(PromotionSchema):
    voucher_id: UUID | None
    original_vnd: int
    discount_vnd: int
    payable_vnd: int
