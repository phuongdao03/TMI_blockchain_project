import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import DossierEvidence
from app.modules.media.models import MediaAsset
from app.modules.notifications.models import Notification
from app.modules.reviews.models import ReviewAssignment, ReviewAssignmentStatus
from app.modules.work_allocations.models import (
    AllocationMember,
    AllocationResponsibility,
    WorkAllocation,
    WorkAllocationKind,
    WorkAllocationStatus,
    WorkScope,
    WorkScopeReviewAssignment,
    WorkScopeType,
)
from app.modules.work_allocations.schemas import ActivateWorkAllocationRequest
from app.modules.work_allocations.service import WorkAllocationService


def _principal(*, user_id: UUID, role: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=uuid4(),
        email=f"{role.lower()}@example.com",
        roles=(role,),
        permissions=(),
    )


def test_dossier_activation_requires_independent_scope_coverage() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(
                    sync_connection,
                    tables=[
                        User.__table__,
                        Role.__table__,
                        UserRole.__table__,
                        AuditLog.__table__,
                        WorkAllocation.__table__,
                        WorkScope.__table__,
                        AllocationMember.__table__,
                        ReviewAssignment.__table__,
                        WorkScopeReviewAssignment.__table__,
                        Notification.__table__,
                        MediaAsset.__table__,
                        DossierEvidence.__table__,
                    ],
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin_id = uuid4()
        reviewer_one_id = uuid4()
        reviewer_two_id = uuid4()
        moderator_role_id = uuid4()
        dossier_id = uuid4()
        version_id = uuid4()
        allocation_id = uuid4()
        dual_scope_id = uuid4()
        regular_scope_id = uuid4()
        evidence_scope_id = uuid4()
        evidence_id = uuid4()
        media_asset_id = uuid4()
        first_assignment_id = uuid4()
        second_assignment_id = uuid4()

        async with sessions.begin() as session:
            session.add_all(
                [
                    User(id=admin_id, email="admin@example.com", password_hash=None),
                    User(
                        id=reviewer_one_id,
                        email="reviewer-one@example.com",
                        password_hash=None,
                        status=UserStatus.ACTIVE,
                    ),
                    User(
                        id=reviewer_two_id,
                        email="reviewer-two@example.com",
                        password_hash=None,
                        status=UserStatus.ACTIVE,
                    ),
                    Role(id=moderator_role_id, code="MODERATOR"),
                    UserRole(user_id=reviewer_one_id, role_id=moderator_role_id),
                    UserRole(user_id=reviewer_two_id, role_id=moderator_role_id),
                    WorkAllocation(
                        id=allocation_id,
                        kind=WorkAllocationKind.DOSSIER_REVIEW,
                        objective="Review complex dossier",
                        dossier_id=dossier_id,
                        dossier_version_id=version_id,
                        created_by_user_id=admin_id,
                    ),
                    WorkScope(
                        id=dual_scope_id,
                        allocation_id=allocation_id,
                        scope_type=WorkScopeType.GROUP,
                        group_label="Legal documents",
                        requires_dual_review=True,
                    ),
                    WorkScope(
                        id=regular_scope_id,
                        allocation_id=allocation_id,
                        scope_type=WorkScopeType.GROUP,
                        group_label="Supporting documents",
                    ),
                    WorkScope(
                        id=evidence_scope_id,
                        allocation_id=allocation_id,
                        scope_type=WorkScopeType.EVIDENCE,
                        dossier_evidence_id=evidence_id,
                    ),
                    DossierEvidence(
                        id=evidence_id,
                        dossier_id=dossier_id,
                        dossier_version_id=version_id,
                        media_asset_id=media_asset_id,
                        evidence_type="DOCUMENT",
                        title="Primary evidence document",
                    ),
                    AllocationMember(
                        allocation_id=allocation_id,
                        user_id=reviewer_one_id,
                        responsibility=AllocationResponsibility.REVIEWER,
                        assigned_by_user_id=admin_id,
                    ),
                    AllocationMember(
                        allocation_id=allocation_id,
                        user_id=reviewer_two_id,
                        responsibility=AllocationResponsibility.REVIEWER,
                        assigned_by_user_id=admin_id,
                    ),
                    ReviewAssignment(
                        id=first_assignment_id,
                        dossier_id=dossier_id,
                        dossier_version_id=version_id,
                        reviewer_user_id=reviewer_one_id,
                        assigned_by=admin_id,
                        status=ReviewAssignmentStatus.IN_PROGRESS,
                    ),
                    ReviewAssignment(
                        id=second_assignment_id,
                        dossier_id=dossier_id,
                        dossier_version_id=version_id,
                        reviewer_user_id=reviewer_two_id,
                        assigned_by=admin_id,
                        status=ReviewAssignmentStatus.IN_PROGRESS,
                    ),
                ]
            )

        admin = _principal(user_id=admin_id, role="SUPER_ADMIN")
        moderator = _principal(user_id=reviewer_one_id, role="MODERATOR")
        complete_coverage = ActivateWorkAllocationRequest.model_validate(
            {
                "scopeCoverage": [
                    {
                        "scopeId": str(dual_scope_id),
                        "reviewAssignmentIds": [
                            str(first_assignment_id),
                            str(second_assignment_id),
                        ],
                    },
                    {
                        "scopeId": str(regular_scope_id),
                        "reviewAssignmentIds": [str(first_assignment_id)],
                    },
                    {
                        "scopeId": str(evidence_scope_id),
                        "reviewAssignmentIds": [str(first_assignment_id)],
                    },
                ]
            }
        )
        incomplete_coverage = ActivateWorkAllocationRequest.model_validate(
            {
                "scopeCoverage": [
                    {
                        "scopeId": str(dual_scope_id),
                        "reviewAssignmentIds": [str(first_assignment_id)],
                    },
                    {
                        "scopeId": str(regular_scope_id),
                        "reviewAssignmentIds": [str(first_assignment_id)],
                    },
                    {
                        "scopeId": str(evidence_scope_id),
                        "reviewAssignmentIds": [str(first_assignment_id)],
                    },
                ]
            }
        )
        async with sessions() as session:
            service = WorkAllocationService(session)
            with pytest.raises(DomainError) as incomplete_error:
                await service.activate_allocation(
                    admin,
                    allocation_id,
                    incomplete_coverage,
                    audit=AuditService(session),
                    request_id="coverage-test",
                    user_agent="pytest",
                )
            assert incomplete_error.value.code == "WORK_ALLOCATION_COVERAGE_INCOMPLETE"
            assert (
                await session.scalar(
                    select(WorkAllocation.status).where(
                        WorkAllocation.id == allocation_id
                    )
                )
                is WorkAllocationStatus.DRAFT
            )

            with pytest.raises(DomainError) as forbidden_error:
                await service.activate_allocation(
                    moderator,
                    allocation_id,
                    complete_coverage,
                    audit=AuditService(session),
                    request_id="coverage-test",
                    user_agent="pytest",
                )
            assert forbidden_error.value.code == "WORK_ALLOCATION_FORBIDDEN"

            activated = await service.activate_allocation(
                admin,
                allocation_id,
                complete_coverage,
                audit=AuditService(session),
                request_id="coverage-test",
                user_agent="pytest",
            )
            assert activated.status is WorkAllocationStatus.ACTIVE
            detail = await service.get_allocation(admin, allocation_id)
            assert len(detail.scopes) == 3
            assert len(detail.members) == 2
            assert {
                coverage.scope_id: len(coverage.reviewer_user_ids)
                for coverage in detail.scope_coverage
            } == {dual_scope_id: 2, regular_scope_id: 1, evidence_scope_id: 1}
            assert {scope.id: scope.dossier_evidence_title for scope in detail.scopes}[
                evidence_scope_id
            ] == "Primary evidence document"
            assert (
                await session.scalar(
                    select(WorkScopeReviewAssignment).where(
                        WorkScopeReviewAssignment.scope_id == dual_scope_id
                    )
                )
                is not None
            )
            assert (
                int(
                    await session.scalar(
                        select(func.count())
                        .select_from(WorkScopeReviewAssignment)
                        .where(WorkScopeReviewAssignment.scope_id == dual_scope_id)
                    )
                    or 0
                )
                == 2
            )
            audit = await session.scalar(
                select(AuditLog).where(AuditLog.action == "work.allocation.activated")
            )
            assert audit is not None
            assert "review_assignment_ids" not in audit.after_json
            with pytest.raises(DomainError) as detail_error:
                await service.get_allocation(moderator, allocation_id)
            assert detail_error.value.code == "WORK_ALLOCATION_FORBIDDEN"

        await engine.dispose()

    asyncio.run(exercise())
