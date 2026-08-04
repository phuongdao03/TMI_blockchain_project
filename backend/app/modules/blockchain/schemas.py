from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.blockchain.models import BlockchainTransactionStatus


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class BlockchainSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class BlockchainTransactionData(BlockchainSchema):
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


class BlockchainQueuedData(BlockchainSchema):
    status: str = "queued"
