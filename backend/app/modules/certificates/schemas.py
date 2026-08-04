from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    CertificateStatus,
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
