from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.blockchain.models import BlockchainTransactionStatus


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
