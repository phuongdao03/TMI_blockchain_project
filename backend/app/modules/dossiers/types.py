from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.dossiers.models import DossierStatus, DossierVisibility


@dataclass(frozen=True, slots=True)
class CreateDossier:
    category_id: UUID
    title: str
    organization_id: UUID | None = None
    slug: str | None = None
    summary: str | None = None
    visibility: DossierVisibility = DossierVisibility.PRIVATE


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
class CreateEvidence:
    media_asset_id: UUID
    evidence_type: str
    title: str
    description: str | None = None
    issued_at: datetime | None = None
    display_order: int = 0
    is_public: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceChanges:
    evidence_type: str | None = None
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
    title: str
    description: str | None
    issued_at: datetime | None
    display_order: int
    is_public: bool
    mime_type: str
    bytes: int
    sha256: str


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
class DossierDetailView:
    dossier: DossierView
    evidences: tuple[EvidenceView, ...]
