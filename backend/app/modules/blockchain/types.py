from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    DocumentEvidenceStatus,
)


@dataclass(frozen=True, slots=True)
class BlockchainTransactionView:
    id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    certificate_id: UUID | None
    network: str
    chain_id: int
    contract_address: str
    method: str
    payload_hash: str
    tx_hash: str | None
    nonce: int | None
    status: BlockchainTransactionStatus
    confirmations: int
    error_code: str | None
    error_message: str | None
    broadcast_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentEvidenceView:
    id: UUID
    document_hash_claim_id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    evidence_key: str
    commitment: str
    version_no: int
    previous_evidence_key: str | None
    recorded_at: datetime
    status: DocumentEvidenceStatus
    transaction_id: UUID
    network: str
    tx_hash: str | None
    confirmations: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime
