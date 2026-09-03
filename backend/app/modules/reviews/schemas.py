from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.dossiers.models import DossierStatus
from app.modules.reviews.models import (
    ReviewAssignmentStatus,
    ReviewFindingAction,
    ReviewFindingSeverity,
    ReviewRecommendation,
    SimilarityCaseDisposition,
    SimilarityCaseStatus,
    SimilaritySignalType,
)


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ReviewSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class TransitionRequest(ReviewSchema):
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]


class DossierTransitionData(ReviewSchema):
    dossier_id: UUID
    status: DossierStatus


class AssignReviewersRequest(ReviewSchema):
    reviewer_user_ids: Annotated[list[UUID], Field(min_length=1, max_length=50)]
    due_at: datetime | None = None

    @field_validator("reviewer_user_ids")
    @classmethod
    def unique_reviewers(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Reviewer IDs must be unique.")
        return value


class ReviewAssignmentData(ReviewSchema):
    id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    reviewer_user_id: UUID
    assigned_by: UUID
    due_at: datetime | None
    status: ReviewAssignmentStatus
    conflict_declared_at: datetime | None
    conflict_reason: str | None


class ConflictDeclarationRequest(ReviewSchema):
    has_conflict: bool
    reason: Annotated[str | None, Field(max_length=2_000)] = None


class ReviewFindingData(ReviewSchema):
    id: UUID
    severity: ReviewFindingSeverity
    criterion: Annotated[str, Field(min_length=1, max_length=64)]
    evidence_media_ids: Annotated[list[UUID], Field(min_length=1, max_length=10)]
    title: Annotated[str, Field(min_length=5, max_length=240)]
    description: Annotated[str, Field(min_length=20, max_length=2_000)]
    action: ReviewFindingAction


class ReviewGateAnswerData(ReviewSchema):
    outcome: Literal["PASS", "FAIL", "NOT_APPLICABLE"]
    rationale: Annotated[str, Field(min_length=20, max_length=2_000)]
    evidence_media_ids: Annotated[list[UUID], Field(max_length=10)] = Field(
        default_factory=list
    )


class SpecialistCriterionAnswerData(ReviewSchema):
    score: Annotated[int, Field(ge=0, le=5)]
    rationale: Annotated[str, Field(min_length=20, max_length=2_000)]
    evidence_media_ids: Annotated[list[UUID], Field(min_length=1, max_length=10)]


class CriterionVerdictData(ReviewSchema):
    outcome: Literal["MEETS", "NEEDS_CLARIFICATION", "DOES_NOT_MEET", "NOT_APPLICABLE"]
    rationale: Annotated[str, Field(max_length=2_000)] = ""
    evidence_media_ids: Annotated[list[UUID], Field(max_length=10)] = Field(
        default_factory=list
    )


class EvidenceAssessmentData(ReviewSchema):
    status: Literal["UNREVIEWED", "VALID", "NEEDS_CLARIFICATION", "NOT_RELEVANT"]
    note: Annotated[str, Field(max_length=1_000)] = ""


class ReviewDraftRequest(ReviewSchema):
    truth_score: Annotated[int | None, Field(ge=0, le=20)] = None
    transparency_score: Annotated[int | None, Field(ge=0, le=20)] = None
    ownership_score: Annotated[int | None, Field(ge=0, le=20)] = None
    professionalism_score: Annotated[int | None, Field(ge=0, le=20)] = None
    respect_score: Annotated[int | None, Field(ge=0, le=20)] = None
    criterion_comments: dict[str, Annotated[str, Field(max_length=2_000)]] = Field(
        default_factory=dict
    )
    criterion_evidence: dict[str, Annotated[list[UUID], Field(max_length=10)]] = Field(
        default_factory=dict
    )
    findings: Annotated[list[ReviewFindingData], Field(max_length=20)] = Field(
        default_factory=list
    )
    checklist_answers: dict[str, bool] = Field(default_factory=dict)
    applicant_feedback: Annotated[str | None, Field(max_length=2_000)] = None
    recommendation: ReviewRecommendation | None = None
    private_note: Annotated[str | None, Field(max_length=5_000)] = None
    gate_answers: dict[str, ReviewGateAnswerData] = Field(default_factory=dict)
    specialist_answers: dict[str, SpecialistCriterionAnswerData] = Field(
        default_factory=dict
    )
    criterion_verdicts: dict[str, CriterionVerdictData] = Field(default_factory=dict)
    evidence_assessments: dict[UUID, EvidenceAssessmentData] = Field(
        default_factory=dict
    )

    @field_validator("criterion_comments")
    @classmethod
    def valid_criteria(cls, value: dict[str, str]) -> dict[str, str]:
        allowed = {
            "truth",
            "transparency",
            "ownership",
            "professionalism",
            "respect",
        }
        if set(value) - allowed:
            raise ValueError("Criterion comment key is invalid.")
        return value

    @field_validator("criterion_evidence")
    @classmethod
    def valid_evidence_criteria(
        cls, value: dict[str, list[UUID]]
    ) -> dict[str, list[UUID]]:
        allowed = {
            "truth",
            "transparency",
            "ownership",
            "professionalism",
            "respect",
        }
        if set(value) - allowed:
            raise ValueError("Criterion evidence key is invalid.")
        return value


class ReviewData(ReviewSchema):
    id: UUID
    assignment_id: UUID
    truth_score: int | None
    transparency_score: int | None
    ownership_score: int | None
    professionalism_score: int | None
    respect_score: int | None
    total_score: int | None
    rubric_version: str | None
    specialist_score: int | None
    recommendation: ReviewRecommendation | None
    criterion_comments: dict[str, str]
    criterion_evidence: dict[str, tuple[UUID, ...]]
    findings: tuple[ReviewFindingData, ...]
    checklist_answers: dict[str, bool]
    applicant_feedback: str | None
    private_note: str | None
    submitted_at: datetime | None
    gate_answers: dict[str, ReviewGateAnswerData]
    specialist_answers: dict[str, SpecialistCriterionAnswerData]
    criterion_verdicts: dict[str, CriterionVerdictData]
    evidence_assessments: dict[UUID, EvidenceAssessmentData]


class ReviewAssignmentSummaryData(ReviewSchema):
    assignment: ReviewAssignmentData
    dossier_code: str
    dossier_title: str
    version_no: int


class ReviewAssignmentDetailData(ReviewAssignmentSummaryData):
    canonical_hash: str | None
    snapshot_json: dict[str, Any] | None
    review: ReviewData | None


class AssignSimilarityCaseRequest(ReviewSchema):
    reviewer_user_id: UUID


class ResolveSimilarityCaseRequest(ReviewSchema):
    disposition: SimilarityCaseDisposition
    reason: Annotated[str, Field(min_length=20, max_length=2_000)]


class SimilarityAssetSummaryData(ReviewSchema):
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version_no: int
    evidence_media_ids: tuple[UUID, ...]


class SimilarityCaseData(ReviewSchema):
    id: UUID
    left_dossier_version_id: UUID
    right_dossier_version_id: UUID
    left_asset: SimilarityAssetSummaryData | None
    right_asset: SimilarityAssetSummaryData | None
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
