from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.dossiers.models import (
    DocumentHashAdjudicationAction,
    DossierStatus,
    DossierVisibility,
    EvidenceVisibility,
)


@dataclass(frozen=True, slots=True)
class CreateDossier:
    category_id: UUID
    title: str
    organization_id: UUID | None = None
    slug: str | None = None
    summary: str | None = None
    visibility: DossierVisibility = DossierVisibility.PRIVATE
    dossier_type_version_id: UUID | None = None
    form_data: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class DossierChanges:
    category_id: UUID | None = None
    title: str | None = None
    organization_id: UUID | None = None
    slug: str | None = None
    summary: str | None = None
    visibility: DossierVisibility | None = None
    provided_fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class DossierView:
    id: UUID
    code: str
    owner_user_id: UUID
    organization_id: UUID | None
    category_id: UUID
    dossier_type_id: UUID | None
    dossier_type_version_id: UUID | None
    form_data: dict[str, Any]
    title: str
    slug: str | None
    summary: str | None
    status: DossierStatus
    visibility: DossierVisibility
    current_version_no: int
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_edit: bool


@dataclass(frozen=True, slots=True)
class DossierPage:
    items: tuple[DossierView, ...]
    total: int


@dataclass(frozen=True, slots=True)
class DossierTypeVersionView:
    id: UUID
    dossier_type_id: UUID
    version_no: int
    schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DossierTypeView:
    id: UUID
    category_id: UUID
    code: str
    name: str
    is_active: bool
    current_version: DossierTypeVersionView


@dataclass(frozen=True, slots=True)
class CreateEvidence:
    media_asset_id: UUID
    evidence_type: str
    title: str
    evidence_role: str | None = None
    access_scope: EvidenceVisibility | None = None
    description: str | None = None
    issued_at: datetime | None = None
    display_order: int = 0
    is_public: bool | None = None


@dataclass(frozen=True, slots=True)
class EvidenceChanges:
    evidence_type: str | None = None
    evidence_role: str | None = None
    access_scope: EvidenceVisibility | None = None
    title: str | None = None
    description: str | None = None
    issued_at: datetime | None = None
    display_order: int | None = None
    is_public: bool | None = None
    provided_fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class EvidenceView:
    id: UUID
    dossier_id: UUID
    dossier_version_id: UUID | None
    media_asset_id: UUID
    evidence_type: str
    evidence_role: str | None
    access_scope: EvidenceVisibility
    title: str
    description: str | None
    issued_at: datetime | None
    display_order: int
    is_public: bool
    mime_type: str
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class DocumentRuleView:
    key: str
    label: str
    document_type: str
    required: bool
    allowed_mime_types: tuple[str, ...]
    max_bytes: int
    max_count: int
    default_visibility: EvidenceVisibility


@dataclass(frozen=True, slots=True)
class DossierVersionView:
    id: UUID
    dossier_id: UUID
    version_no: int
    snapshot_json: dict[str, object]
    canonical_hash: str
    submitted_by: UUID
    submitted_at: datetime


@dataclass(frozen=True, slots=True)
class DossierStatusHistoryView:
    id: UUID
    dossier_id: UUID
    from_status: DossierStatus
    to_status: DossierStatus
    actor_user_id: UUID
    reason_code: str | None
    note: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SubmissionView:
    dossier: DossierView
    version: DossierVersionView


@dataclass(frozen=True, slots=True)
class DocumentHashAdjudicationView:
    id: UUID
    dossier_id: UUID
    media_asset_id: UUID
    action: DocumentHashAdjudicationAction
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DossierDetailView:
    dossier: DossierView
    evidences: tuple[EvidenceView, ...]
    document_rules: tuple[DocumentRuleView, ...]
