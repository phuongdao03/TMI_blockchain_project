from app.modules.work_allocations.models import (
    AllocationMember,
    AllocationResponsibility,
    WorkAllocation,
    WorkAllocationKind,
    WorkAllocationPriority,
    WorkAllocationStatus,
    WorkScope,
    WorkScopeReviewAssignment,
    WorkScopeType,
)


def test_work_allocation_models_are_additive_and_support_dossier_document_scopes() -> (
    None
):
    assert WorkAllocation.__tablename__ == "work_allocations"
    assert WorkScope.__tablename__ == "work_scopes"
    assert AllocationMember.__tablename__ == "allocation_members"
    assert WorkScopeReviewAssignment.__tablename__ == "work_scope_review_assignments"
    assert {item.value for item in WorkAllocationKind} == {
        "GENERIC",
        "DOSSIER_REVIEW",
    }
    assert {item.value for item in WorkScopeType} == {"EVIDENCE", "GROUP"}
    assert {item.value for item in AllocationResponsibility} == {
        "LEAD",
        "CONTRIBUTOR",
        "REVIEWER",
    }
    assert WorkAllocationStatus.ACTIVE.value == "ACTIVE"
    assert WorkAllocationPriority.CRITICAL.value == "CRITICAL"
    assert {
        "dossier_id",
        "dossier_version_id",
        "objective",
        "due_at",
        "priority",
        "status",
    }.issubset(WorkAllocation.__table__.c.keys())
    assert {
        "allocation_id",
        "scope_type",
        "dossier_evidence_id",
        "group_label",
        "requires_dual_review",
    }.issubset(WorkScope.__table__.c.keys())
    assert {
        "allocation_id",
        "user_id",
        "responsibility",
        "is_active",
    }.issubset(AllocationMember.__table__.c.keys())
    assert {
        "scope_id",
        "allocation_member_id",
        "review_assignment_id",
    }.issubset(WorkScopeReviewAssignment.__table__.c.keys())
