from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.blockchain.models import CertificateStatus, CertificateVersionStatus
from app.modules.public.verification import PublicEvidenceProof


@dataclass(frozen=True, slots=True)
class PublicCategoryView:
    id: UUID
    code: str
    name: str
    slug: str | None
    description: str | None
    asset_count: int


@dataclass(frozen=True, slots=True)
class PublicAssetView:
    slug: str
    title: str
    summary: str | None
    category_code: str
    category_name: str
    certificate_number: str
    certificate_status: CertificateStatus
    issued_at: datetime
    transaction_hash: str | None


@dataclass(frozen=True, slots=True)
class PublicAssetDetailView:
    asset: PublicAssetView
    metadata: dict[str, object]
    network: str | None
    contract_address: str | None
    confirmations: int


@dataclass(frozen=True, slots=True)
class PublicMapMarkerView:
    slug: str
    title: str
    category_name: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class PublicHomeView:
    certificate_count: int
    category_count: int
    latest_assets: tuple[PublicAssetView, ...]


@dataclass(frozen=True, slots=True)
class PublicCertificateVersionView:
    version_no: int
    status: CertificateVersionStatus
    metadata_hash: str
    transaction_hash: str | None
    block_number: int | None
    confirmed_at: datetime | None
    created_at: datetime
    issuer_label: str
    documents: tuple[PublicEvidenceProof, ...]
