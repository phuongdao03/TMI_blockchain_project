from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.billing.models import FeeObligationStatus
from app.modules.dossiers.models import DossierStatus
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
    bank_bin: str | None = None
    bank_account_number: str | None = None
    bank_account_name: str | None = None
    transfer_description: str | None = None


class AdminPaymentOrderData(PaymentSchema):
    order: PaymentOrderData
    dossier_code: str
    dossier_title: str


class AdminPaymentHistoryRowData(PaymentSchema):
    order: PaymentOrderData
    dossier_code: str
    dossier_title: str
    applicant_user_id: UUID
    applicant_email: str
    initiated_by_email: str | None


class PaymentStatusHistoryData(PaymentSchema):
    id: UUID
    from_status: str | None
    to_status: str
    source: str
    actor_user_id: UUID | None
    actor_email: str | None
    changed_at: datetime


class AdminPaymentHistorySummaryData(PaymentSchema):
    total: int
    status_counts: dict[str, int]
    total_amount_minor: int
    paid_amount_minor: int


class AdminPaymentHistoryPageData(PaymentSchema):
    rows: list[AdminPaymentHistoryRowData]
    summary: AdminPaymentHistorySummaryData


class AdminPaymentHistoryDetailData(PaymentSchema):
    row: AdminPaymentHistoryRowData
    status_history: list[PaymentStatusHistoryData]


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


class PaymentWaiverRequest(PaymentSchema):
    reason: Annotated[str, Field(min_length=5, max_length=500)]


class PaymentWaiverData(PaymentSchema):
    dossier_id: UUID
    status: DossierStatus
    reason: str


class PaymentCandidateData(PaymentSchema):
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version_no: int


class ManualPaymentConfirmationRequest(PaymentSchema):
    evidence_reference: Annotated[str, Field(min_length=1, max_length=255)]
    note: Annotated[str, Field(min_length=1, max_length=2_000)]


class CancelPaymentOrderRequest(PaymentSchema):
    reason: Annotated[str, Field(min_length=5, max_length=500)]
