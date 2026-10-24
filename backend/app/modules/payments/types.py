from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.dossiers.models import DossierStatus
from app.modules.payments.models import PaymentStatus


@dataclass(frozen=True, slots=True)
class PaymentWaiverView:
    dossier_id: UUID
    status: DossierStatus
    reason: str


@dataclass(frozen=True, slots=True)
class PaymentCandidateView:
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version_no: int


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
    bank_bin: str | None = None
    bank_account_number: str | None = None
    bank_account_name: str | None = None
    transfer_description: str | None = None


@dataclass(frozen=True, slots=True)
class AdminPaymentOrderView:
    order: PaymentOrderView
    dossier_code: str
    dossier_title: str


@dataclass(frozen=True, slots=True)
class AdminPaymentHistoryRowView:
    order: PaymentOrderView
    dossier_code: str
    dossier_title: str
    applicant_user_id: UUID
    applicant_email: str
    initiated_by_email: str | None


@dataclass(frozen=True, slots=True)
class PaymentStatusHistoryView:
    id: UUID
    from_status: str | None
    to_status: str
    source: str
    actor_user_id: UUID | None
    actor_email: str | None
    changed_at: datetime


@dataclass(frozen=True, slots=True)
class AdminPaymentHistorySummaryView:
    total: int
    status_counts: dict[str, int]
    total_amount_minor: int
    paid_amount_minor: int


@dataclass(frozen=True, slots=True)
class AdminPaymentHistoryPageView:
    rows: tuple[AdminPaymentHistoryRowView, ...]
    summary: AdminPaymentHistorySummaryView


@dataclass(frozen=True, slots=True)
class AdminPaymentHistoryDetailView:
    row: AdminPaymentHistoryRowView
    status_history: tuple[PaymentStatusHistoryView, ...]
