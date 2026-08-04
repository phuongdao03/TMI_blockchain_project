from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    CertificateStatus,
)


@dataclass(frozen=True, slots=True)
class CertificateView:
    id: UUID
    certificate_number: str
    dossier_id: UUID
    dossier_code: str
    asset_title: str
    category_name: str
    current_version_no: int
    status: CertificateStatus
    issued_at: datetime
    expires_at: datetime | None
    pdf_ready: bool
    network: str | None
    contract_address: str | None
    transaction_hash: str | None
    blockchain_status: BlockchainTransactionStatus | None
    confirmations: int


@dataclass(frozen=True, slots=True)
class CertificateDetailView:
    certificate: CertificateView
    metadata: dict[str, object]
    metadata_hash: str
    qr_payload: str


@dataclass(frozen=True, slots=True)
class CertificateDownloadView:
    url: str
    expires_at: int
