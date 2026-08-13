from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.modules.auth.models import User
from app.modules.dossiers.models import Dossier, DossierVersion


class ReviewAssignmentStatus(StrEnum):
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    CONFLICTED = "CONFLICTED"
    SUBMITTED = "SUBMITTED"
    CANCELLED = "CANCELLED"


class ReviewRecommendation(StrEnum):
    APPROVE = "APPROVE"
    SUPPLEMENT = "SUPPLEMENT"
    REJECT = "REJECT"


class SimilarityCaseStatus(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    RESOLVED = "RESOLVED"


class SimilaritySignalType(StrEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class SimilarityCaseDisposition(StrEnum):
    DISTINCT = "DISTINCT"
    RELATED = "RELATED"
    SAME_WORK = "SAME_WORK"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda values: [item.value for item in values],
        validate_strings=True,
    )


class ReviewAssignment(Base):
    __tablename__ = "review_assignments"
    __table_args__ = (
        CheckConstraint(
            (
                "status != 'CONFLICTED' OR "
                "(conflict_declared_at IS NOT NULL "
                "AND length(trim(conflict_reason)) > 0)"
            ),
            name="conflicted_reason_required",
        ),
        Index(
            "ix_review_assignments_reviewer_status_due_at",
            "reviewer_user_id",
            "status",
            "due_at",
        ),
        Index(
            "uq_review_assignments_active_reviewer_version",
            "reviewer_user_id",
            "dossier_version_id",
            unique=True,
            sqlite_where=text("status IN ('ASSIGNED', 'IN_PROGRESS')"),
            postgresql_where=text("status IN ('ASSIGNED', 'IN_PROGRESS')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(Dossier.id, ondelete="RESTRICT"),
        nullable=False,
    )
    dossier_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(DossierVersion.id, ondelete="RESTRICT"),
        nullable=False,
    )
    reviewer_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
        nullable=False,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReviewAssignmentStatus] = mapped_column(
        _enum(ReviewAssignmentStatus, "review_assignment_status"),
        nullable=False,
        default=ReviewAssignmentStatus.ASSIGNED,
        server_default=ReviewAssignmentStatus.ASSIGNED.value,
    )
    conflict_declared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    conflict_reason: Mapped[str | None] = mapped_column(Text)


COMMENTS_TYPE = JSONB().with_variant(JSON(), "sqlite")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(
            "truth_score BETWEEN 0 AND 20",
            name="truth_score_range",
        ),
        CheckConstraint(
            "transparency_score BETWEEN 0 AND 20",
            name="transparency_score_range",
        ),
        CheckConstraint(
            "ownership_score BETWEEN 0 AND 20",
            name="ownership_score_range",
        ),
        CheckConstraint(
            "professionalism_score BETWEEN 0 AND 20",
            name="professionalism_score_range",
        ),
        CheckConstraint(
            "respect_score BETWEEN 0 AND 20",
            name="respect_score_range",
        ),
        CheckConstraint(
            "total_score BETWEEN 0 AND 100",
            name="total_score_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(ReviewAssignment.id, ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    truth_score: Mapped[int | None] = mapped_column(SmallInteger)
    transparency_score: Mapped[int | None] = mapped_column(SmallInteger)
    ownership_score: Mapped[int | None] = mapped_column(SmallInteger)
    professionalism_score: Mapped[int | None] = mapped_column(SmallInteger)
    respect_score: Mapped[int | None] = mapped_column(SmallInteger)
    total_score: Mapped[int | None] = mapped_column(SmallInteger)
    recommendation: Mapped[ReviewRecommendation | None] = mapped_column(
        _enum(ReviewRecommendation, "review_recommendation")
    )
    criterion_comments: Mapped[dict[str, str]] = mapped_column(
        COMMENTS_TYPE,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    private_note: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SimilarityReviewCase(Base):
    __tablename__ = "similarity_review_cases"
    __table_args__ = (
        CheckConstraint(
            "left_dossier_version_id != right_dossier_version_id",
            name="similarity_distinct_versions",
        ),
        CheckConstraint(
            "(signal_type = 'TEXT' AND text_score BETWEEN 0 AND 1 "
            "AND image_distance IS NULL) OR "
            "(signal_type = 'IMAGE' AND image_distance BETWEEN 0 AND 64 "
            "AND text_score IS NULL)",
            name="similarity_signal_value",
        ),
        CheckConstraint(
            "(status = 'OPEN' AND assigned_reviewer_user_id IS NULL "
            "AND assigned_by IS NULL AND assigned_at IS NULL) OR "
            "(status = 'ASSIGNED' AND assigned_reviewer_user_id IS NOT NULL "
            "AND assigned_by IS NOT NULL AND assigned_at IS NOT NULL) OR "
            "(status = 'RESOLVED' AND assigned_reviewer_user_id IS NOT NULL "
            "AND disposition IS NOT NULL AND length(trim(resolution_reason)) >= 20 "
            "AND resolved_at IS NOT NULL)",
            name="similarity_case_lifecycle",
        ),
        UniqueConstraint(
            "left_dossier_version_id",
            "right_dossier_version_id",
            "signal_type",
            "policy_version",
            name="uq_similarity_case_pair_signal_policy",
        ),
        Index(
            "ix_similarity_cases_reviewer_status_created",
            "assigned_reviewer_user_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_similarity_cases_status_created",
            "status",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    left_dossier_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(DossierVersion.id, ondelete="RESTRICT"),
        nullable=False,
    )
    right_dossier_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(DossierVersion.id, ondelete="RESTRICT"),
        nullable=False,
    )
    left_version: Mapped[DossierVersion] = relationship(
        foreign_keys=[left_dossier_version_id],
        lazy="joined",
    )
    right_version: Mapped[DossierVersion] = relationship(
        foreign_keys=[right_dossier_version_id],
        lazy="joined",
    )
    signal_type: Mapped[SimilaritySignalType] = mapped_column(
        _enum(SimilaritySignalType, "similarity_signal_type"),
        nullable=False,
    )
    text_score: Mapped[float | None] = mapped_column(Float)
    image_distance: Mapped[int | None] = mapped_column(SmallInteger)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[SimilarityCaseStatus] = mapped_column(
        _enum(SimilarityCaseStatus, "similarity_case_status"),
        nullable=False,
        default=SimilarityCaseStatus.OPEN,
    )
    assigned_reviewer_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
    )
    assigned_by: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(User.id, ondelete="RESTRICT"),
    )
    disposition: Mapped[SimilarityCaseDisposition | None] = mapped_column(
        _enum(SimilarityCaseDisposition, "similarity_disposition")
    )
    resolution_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
