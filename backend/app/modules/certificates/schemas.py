from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    CertificateStatus,
    CertificateVersionStatus,
)


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class CertificateSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class CertificateData(CertificateSchema):
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


class CertificateDetailData(CertificateSchema):
    certificate: CertificateData
    metadata: dict[str, object]
    metadata_hash: str
    qr_payload: str


class CertificateDownloadData(CertificateSchema):
    url: str
    expires_at: int


class CertificateVersionData(CertificateSchema):
    id: UUID
    certificate_id: UUID
    version_no: int
    dossier_version_id: UUID
    predecessor_version_id: UUID | None
    status: CertificateVersionStatus
    change_reason: str | None
    requested_by: UUID | None
    requested_at: datetime | None
    decided_by: UUID | None
    decided_at: datetime | None
    rejection_reason: str | None
    metadata_hash: str
    blockchain_transaction_id: UUID | None
    pdf_ready: bool
    created_at: datetime


class CertificateVersionRequest(CertificateSchema):
    dossier_version_id: UUID
    reason: str = Field(min_length=20, max_length=2_000)


class CertificateVersionDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class CertificateVersionDecisionRequest(CertificateSchema):
    decision: CertificateVersionDecision
    reason: str | None = Field(default=None, min_length=20, max_length=2_000)

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "CertificateVersionDecisionRequest":
        if self.decision is CertificateVersionDecision.REJECT and self.reason is None:
            raise ValueError("A rejection reason is required.")
        if (
            self.decision is CertificateVersionDecision.APPROVE
            and self.reason is not None
        ):
            raise ValueError("An approval does not accept a rejection reason.")
        return self


class CertificateRevocationRequest(CertificateSchema):
    reason: str = Field(min_length=20, max_length=2_000)
