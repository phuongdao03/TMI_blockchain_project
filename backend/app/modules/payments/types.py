from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.payments.models import PaymentStatus


@dataclass(frozen=True, slots=True)
class PaymentOrderView:
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
    description: str | None = None
    due_at: datetime | None = None
    issued_by_user_id: UUID | None = None
    issued_at: datetime | None = None
    fee_obligation_id: UUID | None = None
