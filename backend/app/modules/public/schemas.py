from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    CertificateStatus,
    CertificateVersionStatus,
)
from app.modules.public.models import (
    ContentReportReason,
    ContentReportStatus,
    DerivativeStatus,
    PublicationStatus,
    PublicMediaKind,
    PublicWorkVisibility,
)
from app.modules.public.verification import VerificationStatus


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class PublicSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class PublicCategoryData(PublicSchema):
    id: UUID
    code: str
    name: str
    slug: str | None
    description: str | None
    asset_count: int


class PublicAssetData(PublicSchema):
    slug: str
    title: str
    summary: str | None
    category_code: str
    category_name: str
    certificate_number: str
    certificate_status: CertificateStatus
    issued_at: datetime
    transaction_hash: str | None


class PublicAssetDetailData(PublicSchema):
    asset: PublicAssetData
    metadata: dict[str, object]
    network: str | None
    contract_address: str | None
    confirmations: int


class PublicMapMarkerData(PublicSchema):
    slug: str
    title: str
    category_name: str
    latitude: float
    longitude: float


class PublicHomeData(PublicSchema):
    certificate_count: int
    category_count: int
    latest_assets: list[PublicAssetData]


class VerificationData(PublicSchema):
    status: VerificationStatus
    checked_at: datetime
    certificate_number: str | None
    asset_title: str | None
    category_name: str | None
    issued_at: datetime | None
    expires_at: datetime | None
    version: int | None
    network: str | None
    contract_address: str | None
    transaction_hash: str | None
    confirmations: int
    confirmed_at: datetime | None
    explorer_url: str | None
    dossier_code: str | None
    metadata_hash: str | None
    block_number: int | None
    issuer_label: str | None
    documents: list["PublicEvidenceProofData"]


class PublicEvidenceProofData(PublicSchema):
    title: str
    evidence_type: str
    sha256: str


class PublicDossierDocumentData(PublicSchema):
    """Public metadata only; never a source-object location or download URL."""

    title: str
    evidence_type: str
    access_scope: Literal["PUBLIC", "PUBLIC_PREVIEW"]
    mime_type: str
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PublicDossierFieldData(PublicSchema):
    """Explicitly approved dynamic dossier field frozen at submission time."""

    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=255)
    value: str | int | float | bool | list[str]


class PublicDossierCertificateData(PublicSchema):
    certificate_number: str
    status: CertificateStatus
    issued_at: datetime
    expires_at: datetime | None
    version: int = Field(ge=1)
    network: str | None
    transaction_hash: str | None
    confirmations: int = Field(ge=0)
    confirmed_at: datetime | None


class PublicDossierVerificationData(PublicSchema):
    """Allowlisted result for a stable public dossier verification code."""

    code: str
    title: str
    summary: str | None
    category_name: str
    published_at: datetime | None
    certificate: PublicDossierCertificateData | None
    public_fields: list[PublicDossierFieldData]
    documents: list[PublicDossierDocumentData]


class PublicCertificateVersionData(PublicSchema):
    version_no: int
    status: CertificateVersionStatus
    metadata_hash: str
    transaction_hash: str | None
    block_number: int | None
    confirmed_at: datetime | None
    created_at: datetime
    issuer_label: str
    documents: list[PublicEvidenceProofData]


class PublicWorkAdminData(PublicSchema):
    id: UUID
    dossier_id: UUID
    certificate_id: UUID | None
    slug: str
    title: str
    short_description: str
    publication_status: PublicationStatus
    visibility: PublicWorkVisibility
    published_at: datetime | None
    scheduled_publish_at: datetime | None
    featured_at: datetime | None
    featured_until: datetime | None
    version: int


class PublicationRequest(PublicSchema):
    expected_version: int = Field(ge=1)
    visibility: PublicWorkVisibility = PublicWorkVisibility.PUBLIC


class PublicationScheduleRequest(PublicationRequest):
    publish_at: datetime


class PublicationVersionRequest(PublicSchema):
    expected_version: int = Field(ge=1)


class PublicationReasonRequest(PublicationVersionRequest):
    reason: str = Field(min_length=3, max_length=1000)


class FeaturedWindowRequest(PublicationVersionRequest):
    featured_at: datetime
    featured_until: datetime | None = None


class PublicWorkEditorRequest(PublicationVersionRequest):
    slug: str = Field(min_length=1, max_length=180)
    title: str = Field(min_length=3, max_length=255)
    short_description: str = Field(min_length=10, max_length=500)
    full_description: str | None = Field(default=None, max_length=20_000)
    author_display_name: str | None = Field(default=None, max_length=255)
    category_id: UUID
    tag_ids: list[UUID] = Field(default_factory=list, max_length=50)
    visibility: PublicWorkVisibility
    thumbnail_media_id: UUID | None = None


class PublicationChecklistData(PublicSchema):
    code: str
    passed: bool


class PublicWorkEditorData(PublicSchema):
    id: UUID
    dossier_id: UUID
    certificate_id: UUID | None
    slug: str
    title: str
    short_description: str
    full_description: str | None
    author_display_name: str | None
    category_id: UUID
    category_name: str
    tag_ids: list[UUID]
    thumbnail_media_id: UUID | None
    publication_status: PublicationStatus
    visibility: PublicWorkVisibility
    published_at: datetime | None
    scheduled_publish_at: datetime | None
    featured_at: datetime | None
    featured_until: datetime | None
    version: int
    checklist: list[PublicationChecklistData]


class PublicWorkPreviewData(PublicSchema):
    slug: str
    title: str
    short_description: str
    full_description: str | None
    author_display_name: str | None
    category_name: str
    media: list["PublicMediaData"]
    can_publish: bool


class TaxonomyCategoryRequest(PublicSchema):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    parent_id: UUID | None = None
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True
    code: str | None = Field(default=None, min_length=1, max_length=64)


class TaxonomyCategoryData(PublicSchema):
    id: UUID
    parent_id: UUID | None
    code: str
    name: str
    slug: str | None
    description: str | None
    is_active: bool
    display_order: int


class TaxonomyTagRequest(PublicSchema):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=160)
    is_active: bool = True


class TaxonomyTagData(PublicSchema):
    id: UUID
    name: str
    slug: str
    is_active: bool


class WorkTagAssignmentRequest(PublicSchema):
    tag_ids: list[UUID] = Field(max_length=50)


class PublicMediaAttachRequest(PublicSchema):
    media_asset_id: UUID
    sort_order: int = Field(default=0, ge=0)
    caption: str | None = Field(default=None, max_length=500)
    alt_text: str | None = Field(default=None, max_length=500)


class PublicMediaOrderRequest(PublicSchema):
    relation_ids: list[UUID] = Field(max_length=100)


class PublicMediaAdminData(PublicSchema):
    id: UUID
    media_asset_id: UUID
    media_kind: PublicMediaKind
    sort_order: int
    caption: str | None
    alt_text: str | None
    derivative_status: DerivativeStatus
    derivative_mime_type: str | None
    derivative_width: int | None
    derivative_height: int | None
    duration_ms: int | None
    attempt_count: int
    failure_code: str | None


class PublicWorkTagData(PublicSchema):
    name: str
    slug: str


class PublicWorkCardData(PublicSchema):
    id: UUID
    slug: str
    title: str
    short_description: str
    author_display_name: str | None
    category_name: str
    category_slug: str
    tags: list[PublicWorkTagData]
    published_at: datetime
    is_featured: bool
    thumbnail_url: str | None
    thumbnail_alt_text: str | None


class PublicCertificateSummaryData(PublicSchema):
    certificate_number: str
    status: CertificateStatus
    issued_at: datetime
    expires_at: datetime | None


class PublicProofSummaryData(PublicSchema):
    network: str
    transaction_hash: str | None
    status: BlockchainTransactionStatus
    confirmations: int
    confirmed_at: datetime | None


class PublicMediaData(PublicSchema):
    id: UUID
    kind: PublicMediaKind
    sort_order: int
    caption: str | None
    alt_text: str | None
    url: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    duration_ms: int | None
    is_thumbnail: bool


class PublicWorkDetailProjectionData(PublicSchema):
    id: UUID
    slug: str
    title: str
    short_description: str
    full_description: str | None
    author_display_name: str | None
    organization_display_name: str | None
    category_name: str
    category_slug: str
    tags: list[PublicWorkTagData]
    published_at: datetime
    visibility: PublicWorkVisibility
    certificate: PublicCertificateSummaryData | None
    proof: PublicProofSummaryData | None
    media: list[PublicMediaData]
    related_works: list[PublicWorkCardData]
    canonical_slug: str
    redirected: bool


class PublicSitemapManifestData(PublicSchema):
    generation: str
    total: int
    page_size: int
    page_count: int
    generated_at: datetime


class PublicSitemapEntryData(PublicSchema):
    slug: str
    last_modified: datetime


class ContentReportRequest(PublicSchema):
    reason: ContentReportReason
    description: str | None = Field(default=None, max_length=2_000)
    reporter_email: EmailStr | None = None
    captcha_token: SecretStr | None = Field(default=None, max_length=2_048)


class ContentReportAcceptedData(PublicSchema):
    id: UUID
    status: ContentReportStatus


class ContentReportAdminData(PublicSchema):
    id: UUID
    public_work_id: UUID
    work_title: str
    work_slug: str
    work_version: int
    reason: ContentReportReason
    description: str | None
    status: ContentReportStatus
    reporter_type: str
    has_contact_email: bool
    assigned_to_user_id: UUID | None
    resolution_note: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ContentReportTransitionRequest(PublicSchema):
    status: ContentReportStatus
    resolution_note: str | None = Field(default=None, max_length=2_000)


class ContentReportSuspendRequest(PublicSchema):
    expected_work_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2_000)
