from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class WorkAllocationKind(StrEnum):
    GENERIC = "GENERIC"
    DOSSIER_REVIEW = "DOSSIER_REVIEW"


class WorkAllocationStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkAllocationPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WorkScopeType(StrEnum):
    EVIDENCE = "EVIDENCE"
    GROUP = "GROUP"


class AllocationResponsibility(StrEnum):
    LEAD = "LEAD"
    CONTRIBUTOR = "CONTRIBUTOR"
    REVIEWER = "REVIEWER"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda values: [value.value for value in values],
        validate_strings=True,
        native_enum=False,
        create_constraint=True,
    )


class WorkAllocation(UtcTimestampMixin, Base):
    """An additive work container; it never replaces Task or ReviewAssignment."""

    __tablename__ = "work_allocations"
    __table_args__ = (
        CheckConstraint(
            "(kind = 'GENERIC' AND dossier_id IS NULL AND dossier_version_id IS NULL) "
            "OR (kind = 'DOSSIER_REVIEW' AND dossier_id IS NOT NULL "
            "AND dossier_version_id IS NOT NULL)",
            name="work_allocation_dossier_reference",
        ),
        Index("ix_work_allocations_status_due", "status", "due_at"),
        Index(
            "ix_work_allocations_dossier_version_status",
            "dossier_version_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    kind: Mapped[WorkAllocationKind] = mapped_column(
        _enum(WorkAllocationKind, "work_allocation_kind"), nullable=False
    )
    objective: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    dossier_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("dossiers.id", ondelete="RESTRICT")
    )
    dossier_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("dossier_versions.id", ondelete="RESTRICT")
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[WorkAllocationPriority] = mapped_column(
        _enum(WorkAllocationPriority, "work_allocation_priority"),
        nullable=False,
        default=WorkAllocationPriority.MEDIUM,
        server_default=WorkAllocationPriority.MEDIUM.value,
    )
    status: Mapped[WorkAllocationStatus] = mapped_column(
        _enum(WorkAllocationStatus, "work_allocation_status"),
        nullable=False,
        default=WorkAllocationStatus.DRAFT,
        server_default=WorkAllocationStatus.DRAFT.value,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class WorkScope(UtcTimestampMixin, Base):
    """One immutable-document or logical-document-group unit of coverage."""

    __tablename__ = "work_scopes"
    __table_args__ = (
        CheckConstraint(
            "(scope_type = 'EVIDENCE' AND dossier_evidence_id IS NOT NULL "
            "AND group_label IS NULL) OR "
            "(scope_type = 'GROUP' AND dossier_evidence_id IS NULL "
            "AND length(trim(group_label)) BETWEEN 1 AND 240)",
            name="work_scope_source",
        ),
        UniqueConstraint(
            "allocation_id",
            "dossier_evidence_id",
            name="uq_work_scopes_allocation_evidence",
        ),
        UniqueConstraint(
            "allocation_id",
            "group_label",
            name="uq_work_scopes_allocation_group_label",
        ),
        Index("ix_work_scopes_allocation", "allocation_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    allocation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("work_allocations.id", ondelete="RESTRICT"), nullable=False
    )
    scope_type: Mapped[WorkScopeType] = mapped_column(
        _enum(WorkScopeType, "work_scope_type"), nullable=False
    )
    dossier_evidence_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("dossier_evidences.id", ondelete="RESTRICT")
    )
    group_label: Mapped[str | None] = mapped_column(String(240))
    requires_dual_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class AllocationMember(UtcTimestampMixin, Base):
    """A responsible person retained even after their assignment is deactivated."""

    __tablename__ = "allocation_members"
    __table_args__ = (
        CheckConstraint(
            "(is_active = true AND deactivated_at IS NULL) OR "
            "(is_active = false AND deactivated_at IS NOT NULL)",
            name="allocation_member_active_lifecycle",
        ),
        UniqueConstraint(
            "allocation_id", "user_id", name="uq_allocation_members_allocation_user"
        ),
        Index("ix_allocation_members_user_active", "user_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    allocation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("work_allocations.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    responsibility: Mapped[AllocationResponsibility] = mapped_column(
        _enum(AllocationResponsibility, "allocation_responsibility"), nullable=False
    )
    assigned_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkScopeReviewAssignment(UtcTimestampMixin, Base):
    """Connect a document scope to the authoritative review assignment."""

    __tablename__ = "work_scope_review_assignments"
    __table_args__ = (
        UniqueConstraint(
            "scope_id",
            "review_assignment_id",
            name="uq_work_scope_review_assignments_scope_review_assignment",
        ),
        Index(
            "ix_work_scope_review_assignments_scope",
            "scope_id",
        ),
        Index(
            "ix_work_scope_review_assignments_review_assignment",
            "review_assignment_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    scope_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("work_scopes.id", ondelete="RESTRICT"), nullable=False
    )
    allocation_member_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("allocation_members.id", ondelete="RESTRICT"), nullable=False
    )
    review_assignment_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("review_assignments.id", ondelete="RESTRICT"), nullable=False
    )
