from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.work_allocations.models import (
    AllocationResponsibility,
    WorkAllocationKind,
    WorkAllocationPriority,
    WorkAllocationStatus,
    WorkScopeType,
)


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class WorkAllocationSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="forbid",
    )


class WorkScopeInput(WorkAllocationSchema):
    scope_type: WorkScopeType
    dossier_evidence_id: UUID | None = None
    group_label: Annotated[str | None, Field(max_length=240)] = None
    requires_dual_review: bool = False

    @field_validator("group_label")
    @classmethod
    def normalize_group_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Scope group label must not be blank.")
        return normalized

    @model_validator(mode="after")
    def require_exactly_one_scope_source(self) -> "WorkScopeInput":
        is_evidence = self.scope_type is WorkScopeType.EVIDENCE
        if (
            is_evidence
            and self.dossier_evidence_id is not None
            and self.group_label is None
        ):
            return self
        if (
            not is_evidence
            and self.dossier_evidence_id is None
            and self.group_label is not None
        ):
            return self
        raise ValueError("Scope type must match exactly one document source.")


class AllocationMemberInput(WorkAllocationSchema):
    user_id: UUID
    responsibility: AllocationResponsibility


class WorkScopeCoverageInput(WorkAllocationSchema):
    scope_id: UUID
    review_assignment_ids: Annotated[list[UUID], Field(min_length=1, max_length=20)]

    @field_validator("review_assignment_ids")
    @classmethod
    def require_distinct_assignments(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("A review assignment can cover a scope only once.")
        return value


class ActivateWorkAllocationRequest(WorkAllocationSchema):
    scope_coverage: Annotated[list[WorkScopeCoverageInput], Field(max_length=200)]

    @field_validator("scope_coverage")
    @classmethod
    def require_distinct_scopes(
        cls, value: list[WorkScopeCoverageInput]
    ) -> list[WorkScopeCoverageInput]:
        scope_ids = [coverage.scope_id for coverage in value]
        if len(scope_ids) != len(set(scope_ids)):
            raise ValueError("Each scope can have one coverage declaration.")
        return value


class CreateWorkAllocationRequest(WorkAllocationSchema):
    kind: WorkAllocationKind
    objective: Annotated[str, Field(min_length=1, max_length=240)]
    description: Annotated[str | None, Field(max_length=10_000)] = None
    dossier_id: UUID | None = None
    dossier_version_id: UUID | None = None
    due_at: datetime | None = None
    priority: WorkAllocationPriority = WorkAllocationPriority.MEDIUM
    scopes: list[WorkScopeInput] = Field(default_factory=list, max_length=200)
    members: list[AllocationMemberInput] = Field(default_factory=list, max_length=100)

    @field_validator("objective", "description")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Work allocation text must not be blank.")
        return normalized

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Due time must include a timezone offset.")
        return value

    @model_validator(mode="after")
    def validate_allocation_shape(self) -> "CreateWorkAllocationRequest":
        has_dossier_reference = (
            self.dossier_id is not None or self.dossier_version_id is not None
        )
        if self.kind is WorkAllocationKind.GENERIC:
            if has_dossier_reference or self.scopes:
                raise ValueError("Generic work cannot contain dossier scopes.")
        elif self.dossier_id is None or self.dossier_version_id is None:
            raise ValueError("Dossier review work requires dossier and version IDs.")
        elif not self.scopes:
            raise ValueError("Dossier review work requires at least one scope.")

        evidence_ids = [
            scope.dossier_evidence_id
            for scope in self.scopes
            if scope.dossier_evidence_id is not None
        ]
        group_labels = [
            scope.group_label.casefold()
            for scope in self.scopes
            if scope.group_label is not None
        ]
        member_ids = [member.user_id for member in self.members]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Each document can appear in only one scope.")
        if len(group_labels) != len(set(group_labels)):
            raise ValueError("Each document group can appear in only one scope.")
        if len(member_ids) != len(set(member_ids)):
            raise ValueError(
                "A person can have only one responsibility per allocation."
            )
        return self


class WorkScopeData(WorkAllocationSchema):
    id: UUID
    allocation_id: UUID
    scope_type: WorkScopeType
    dossier_evidence_id: UUID | None
    dossier_evidence_title: str | None = None
    group_label: str | None
    requires_dual_review: bool
    created_at: datetime
    updated_at: datetime


class AllocationMemberData(WorkAllocationSchema):
    id: UUID
    allocation_id: UUID
    user_id: UUID
    responsibility: AllocationResponsibility
    assigned_by_user_id: UUID
    is_active: bool
    deactivated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkScopeCoverageData(WorkAllocationSchema):
    scope_id: UUID
    review_assignment_ids: list[UUID]
    reviewer_user_ids: list[UUID]


class WorkAllocationData(WorkAllocationSchema):
    id: UUID
    kind: WorkAllocationKind
    objective: str
    description: str | None
    dossier_id: UUID | None
    dossier_version_id: UUID | None
    due_at: datetime | None
    priority: WorkAllocationPriority
    status: WorkAllocationStatus
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class WorkAllocationDetailData(WorkAllocationData):
    scopes: list[WorkScopeData]
    members: list[AllocationMemberData]
    scope_coverage: list[WorkScopeCoverageData]
