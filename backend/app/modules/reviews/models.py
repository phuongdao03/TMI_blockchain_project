from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
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
