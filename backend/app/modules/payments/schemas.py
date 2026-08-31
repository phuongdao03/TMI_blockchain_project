from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.billing.models import FeeObligationStatus
from app.modules.payments.models import PaymentStatus


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class PaymentSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class PaymentOrderData(PaymentSchema):
    id: UUID
    order_code: str
    dossier_id: UUID
    fee_obligation_id: UUID | None = None
    provider: str
    provider_order_id: str | None
    amount_minor: int
    currency: str
    status: PaymentStatus
    expires_at: datetime
    paid_at: datetime | None
    checkout_url: str | None
    qr_payload: str | None
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    due_at: datetime | None = None
    issued_by_user_id: UUID | None = None
    issued_at: datetime | None = None


class FeeObligationData(PaymentSchema):
    id: UUID
    dossier_id: UUID
    service_code: str
    description: str
    amount_minor: int
    currency: str
    tax_mode: str
    status: FeeObligationStatus
    due_at: datetime
    paid_at: datetime | None


class IssuePaymentOrderRequest(PaymentSchema):
    amount_minor: Annotated[int, Field(ge=1_000, le=1_000_000_000)]
    currency: Annotated[str, Field(pattern="^VND$")] = "VND"
    description: Annotated[str, Field(min_length=5, max_length=255)]
    due_at: datetime | None = None


class ManualPaymentConfirmationRequest(PaymentSchema):
    evidence_reference: Annotated[str, Field(min_length=1, max_length=255)]
    note: Annotated[str, Field(min_length=1, max_length=2_000)]


class CancelPaymentOrderRequest(PaymentSchema):
    reason: Annotated[str, Field(min_length=5, max_length=500)]
