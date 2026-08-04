from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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


class ManualPaymentConfirmationRequest(PaymentSchema):
    evidence_reference: Annotated[str, Field(min_length=1, max_length=255)]
    note: Annotated[str, Field(min_length=1, max_length=2_000)]
