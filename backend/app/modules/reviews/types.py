from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.modules.dossiers.models import DossierStatus
from app.modules.reviews.models import (
    ReviewAssignmentStatus,
    ReviewRecommendation,
    SimilarityCaseDisposition,
    SimilarityCaseStatus,
    SimilaritySignalType,
)


@dataclass(frozen=True, slots=True)
class DossierTransitionView:
    dossier_id: UUID
    status: DossierStatus


@dataclass(frozen=True, slots=True)
class ReviewAssignmentView:
    id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    reviewer_user_id: UUID
    assigned_by: UUID
    due_at: datetime | None
    status: ReviewAssignmentStatus
    conflict_declared_at: datetime | None
    conflict_reason: str | None


@dataclass(frozen=True, slots=True)
class ReviewDraft:
    truth_score: int | None = None
    transparency_score: int | None = None
    ownership_score: int | None = None
    professionalism_score: int | None = None
    respect_score: int | None = None
    criterion_comments: Mapping[str, str] = field(default_factory=dict)
    recommendation: ReviewRecommendation | None = None
    private_note: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewView:
    id: UUID
    assignment_id: UUID
    truth_score: int | None
    transparency_score: int | None
    ownership_score: int | None
    professionalism_score: int | None
    respect_score: int | None
    total_score: int | None
    recommendation: ReviewRecommendation | None
    criterion_comments: Mapping[str, str]
    private_note: str | None
    submitted_at: datetime | None


@dataclass(frozen=True, slots=True)
class ReviewAssignmentSummaryView:
    assignment: ReviewAssignmentView
    dossier_code: str
    dossier_title: str
    version_no: int


@dataclass(frozen=True, slots=True)
class ReviewAssignmentPage:
    items: tuple[ReviewAssignmentSummaryView, ...]
    total: int


@dataclass(frozen=True, slots=True)
class ReviewAssignmentDetailView:
    assignment: ReviewAssignmentView
    dossier_code: str
    dossier_title: str
    version_no: int
    canonical_hash: str | None
    snapshot_json: Mapping[str, object] | None
    review: ReviewView | None


@dataclass(frozen=True, slots=True)
class SimilarityAssetSummary:
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version_no: int
    evidence_media_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class SimilarityCaseView:
    id: UUID
    left_dossier_version_id: UUID
    right_dossier_version_id: UUID
    left_asset: SimilarityAssetSummary | None
    right_asset: SimilarityAssetSummary | None
    signal_type: SimilaritySignalType
    text_score: float | None
    image_distance: int | None
    policy_version: str
    status: SimilarityCaseStatus
    assigned_reviewer_user_id: UUID | None
    disposition: SimilarityCaseDisposition | None
    resolution_reason: str | None
    created_at: datetime
    assigned_at: datetime | None
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class SimilarityCasePage:
    items: tuple[SimilarityCaseView, ...]
    total: int
