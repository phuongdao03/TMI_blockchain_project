from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    BlockchainWalletLinkStatus,
    DocumentEvidenceStatus,
)
from app.modules.blockchain.verification import DocumentVerificationStatus


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


class DocumentEvidenceData(BlockchainSchema):
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


class DocumentVerificationData(BlockchainSchema):
    status: DocumentVerificationStatus
    checked_at: datetime


class WalletChallengeRequest(BlockchainSchema):
    wallet_address: str = Field(min_length=42, max_length=42)
    chain_id: int = Field(gt=0)


class WalletChallengeData(BlockchainSchema):
    id: UUID
    message: str
    nonce: str
    expires_at: datetime


class WalletLinkVerificationRequest(BlockchainSchema):
    challenge_id: UUID
    nonce: str = Field(min_length=16, max_length=256)
    signature: str = Field(min_length=10, max_length=256)


class WalletLinkData(BlockchainSchema):
    id: UUID
    wallet_address: str
    chain_id: int
    status: BlockchainWalletLinkStatus
    verified_at: datetime


class SigningQueueItemData(BlockchainSchema):
    transaction_id: UUID
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    dossier_version_no: int
    certificate_number: str | None
    proof_hash: str
    status: BlockchainTransactionStatus
    tx_hash: str | None
    error_code: str | None
    created_at: datetime


class SigningContextData(BlockchainSchema):
    transaction_id: UUID
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    dossier_version_no: int
    certificate_number: str | None
    method: str
    proof_hash: str
    network: str
    chain_id: int
    contract_address: str
    status: BlockchainTransactionStatus


class SigningIntentRequest(BlockchainSchema):
    connected_wallet: str = Field(min_length=42, max_length=42)


class SigningIntentData(BlockchainSchema):
    id: UUID
    transaction_id: UUID
    transaction_request: dict[str, str]
    expires_at: datetime
    estimated_gas: int
    gas_price_wei: int
    wallet_balance_wei: int


class SigningSubmissionRequest(BlockchainSchema):
    intent_id: UUID
    transaction_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    connected_wallet: str = Field(min_length=42, max_length=42)


class SigningStatusData(BlockchainSchema):
    transaction_id: UUID
    status: BlockchainTransactionStatus
    tx_hash: str | None
    confirmations: int
    error_code: str | None
    error_message: str | None
    confirmed_at: datetime | None


class THVProofRegistryIntentRequest(BlockchainSchema):
    connected_wallet: str = Field(min_length=42, max_length=42)


class THVProofRegistryQueueItemData(BlockchainSchema):
    transaction_id: UUID | None
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version: int
    proof_hash: str
    status: BlockchainTransactionStatus
    tx_hash: str | None
    confirmations: int
    error_code: str | None
    created_at: datetime


class THVProofRegistryIntentData(BlockchainSchema):
    intent_id: UUID
    transaction_id: UUID
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version: int
    asset_id: str
    proof_hash: str
    network: str
    chain_id: int
    contract_address: str
    transaction_request: dict[str, str]
    estimated_gas: int
    gas_price_wei: int
    wallet_balance_wei: int
    expires_at: datetime


class THVProofRegistrySubmissionRequest(BlockchainSchema):
    intent_id: UUID
    transaction_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    connected_wallet: str = Field(min_length=42, max_length=42)


class THVProofRegistryStatusData(BlockchainSchema):
    transaction_id: UUID
    status: BlockchainTransactionStatus
    tx_hash: str | None
    confirmations: int
    error_code: str | None
    error_message: str | None
    confirmed_at: datetime | None


class THVProofRegistryProofData(BlockchainSchema):
    asset_id: str
    proof_hash: str
    version: int
    recorded_at: int
    signer: str
    exists: bool


class THVProofRegistryVerificationData(BlockchainSchema):
    asset_id: str
    version: int
    expected_hash: str
    verified: bool
