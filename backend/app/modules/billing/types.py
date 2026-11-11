from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.billing.models import FeeObligationStatus


@dataclass(frozen=True, slots=True)
class FeeObligationView:
    id: UUID
    dossier_id: UUID
    owner_user_id: UUID
    price_catalog_version_id: UUID | None
    price_catalog_entry_id: UUID | None
    service_code: str
    description: str
    amount_minor: int
    currency: str
    tax_mode: str
    status: FeeObligationStatus
    due_at: datetime
    paid_at: datetime | None
    fee_type: str | None = None
    fee_policy_id: UUID | None = None
    fee_policy_version_no: int | None = None
    gross_amount_minor: int | None = None
    waiver_amount_minor: int | None = None
