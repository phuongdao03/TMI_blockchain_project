from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.dossiers.models import DossierStatus
from app.modules.reviews.models import (
    ReviewAssignmentStatus,
    ReviewRecommendation,
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


class ReviewDraftRequest(ReviewSchema):
    truth_score: Annotated[int | None, Field(ge=0, le=20)] = None
    transparency_score: Annotated[int | None, Field(ge=0, le=20)] = None
    ownership_score: Annotated[int | None, Field(ge=0, le=20)] = None
    professionalism_score: Annotated[int | None, Field(ge=0, le=20)] = None
    respect_score: Annotated[int | None, Field(ge=0, le=20)] = None
    criterion_comments: dict[str, Annotated[str, Field(max_length=2_000)]] = Field(
        default_factory=dict
    )
    recommendation: ReviewRecommendation | None = None
    private_note: Annotated[str | None, Field(max_length=5_000)] = None

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


class ReviewData(ReviewSchema):
    id: UUID
    assignment_id: UUID
    truth_score: int | None
    transparency_score: int | None
    ownership_score: int | None
    professionalism_score: int | None
    respect_score: int | None
    total_score: int | None
    recommendation: ReviewRecommendation | None
    criterion_comments: dict[str, str]
    private_note: str | None
    submitted_at: datetime | None


class ReviewAssignmentSummaryData(ReviewSchema):
    assignment: ReviewAssignmentData
    dossier_code: str
    dossier_title: str
    version_no: int


class ReviewAssignmentDetailData(ReviewAssignmentSummaryData):
    canonical_hash: str | None
    snapshot_json: dict[str, Any] | None
    review: ReviewData | None
