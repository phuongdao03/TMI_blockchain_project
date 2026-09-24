from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import DossierEvidence, DossierVersion
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
)
from app.modules.work_allocations.schemas import (
    ActivateWorkAllocationRequest,
    AllocationMemberData,
    CreateWorkAllocationRequest,
    WorkAllocationData,
    WorkAllocationDetailData,
    WorkScopeCoverageData,
    WorkScopeData,
)


class WorkAllocationService:
    """Create and list additive work allocations without replacing review records."""

    READ_OWN_ALLOCATIONS = PolicyRequirement(
        permission="work.allocations.read",
        compatible_roles=frozenset({"MODERATOR"}),
        allow_super_admin=False,
    )
    COVERAGE_ASSIGNMENT_STATUSES = frozenset(
        {
            ReviewAssignmentStatus.ASSIGNED,
            ReviewAssignmentStatus.IN_PROGRESS,
            ReviewAssignmentStatus.SUBMITTED,
        }
    )

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _forbidden() -> DomainError:
        return DomainError(
            code="WORK_ALLOCATION_FORBIDDEN",
            message="You do not have permission to access work allocations.",
            status_code=403,
        )

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        # Assignment management changes dossier ownership and is a
        # Super-Admin-only operation. A misconfigured granular permission must
        # not turn into role elevation for an otherwise incompatible account.
        AuthorizationPolicy.require_resource_scope(
            "SUPER_ADMIN" in principal.roles, WorkAllocationService._forbidden
        )

    @classmethod
    def _require_moderator(cls, principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            cls.READ_OWN_ALLOCATIONS,
            cls._forbidden,
        )

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)

    @classmethod
    def _data(cls, allocation: WorkAllocation) -> WorkAllocationData:
        return WorkAllocationData.model_validate(
            {
                field: cls._as_utc(getattr(allocation, field))
                if field in {"due_at", "created_at", "updated_at"}
                else getattr(allocation, field)
                for field in WorkAllocationData.model_fields
            }
        )

    @classmethod
    def _scope_data(cls, scope: WorkScope) -> WorkScopeData:
        return WorkScopeData.model_validate(
            {
                field: (
                    None
                    if field == "dossier_evidence_title"
                    else cls._as_utc(getattr(scope, field))
                    if field in {"created_at", "updated_at"}
                    else getattr(scope, field)
                )
                for field in WorkScopeData.model_fields
            }
        )

    @classmethod
    def _member_data(cls, member: AllocationMember) -> AllocationMemberData:
        return AllocationMemberData.model_validate(
            {
                field: cls._as_utc(getattr(member, field))
                if field in {"deactivated_at", "created_at", "updated_at"}
                else getattr(member, field)
                for field in AllocationMemberData.model_fields
            }
        )

    async def create_allocation(
        self,
        principal: AuthPrincipal,
        payload: CreateWorkAllocationRequest,
        *,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> WorkAllocationData:
        self._require_admin(principal)
        await self._validate_members(payload)
        await self._validate_dossier_scopes(payload)

        allocation = WorkAllocation(
            kind=payload.kind,
            objective=payload.objective,
            description=payload.description,
            dossier_id=payload.dossier_id,
            dossier_version_id=payload.dossier_version_id,
            due_at=self._as_utc(payload.due_at),
            priority=payload.priority,
            created_by_user_id=principal.user_id,
        )
        self._session.add(allocation)
        await self._session.flush()

        self._session.add_all(
            [
                WorkScope(
                    allocation_id=allocation.id,
                    scope_type=scope.scope_type,
                    dossier_evidence_id=scope.dossier_evidence_id,
                    group_label=scope.group_label,
                    requires_dual_review=scope.requires_dual_review,
                )
                for scope in payload.scopes
            ]
        )
        self._session.add_all(
            [
                AllocationMember(
                    allocation_id=allocation.id,
                    user_id=member.user_id,
                    responsibility=member.responsibility,
                    assigned_by_user_id=principal.user_id,
                )
                for member in payload.members
            ]
        )
        audit.record(
            actor_user_id=principal.user_id,
            action="work.allocation.created",
            resource_type="work_allocation",
            resource_id=str(allocation.id),
            after={
                "kind": allocation.kind.value,
                "status": allocation.status.value,
                "priority": allocation.priority.value,
                "due_at": (
                    allocation.due_at.astimezone(UTC).isoformat()
                    if allocation.due_at is not None
                    else None
                ),
                "scope_count": len(payload.scopes),
                "member_count": len(payload.members),
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        await self._session.refresh(allocation)
        return self._data(allocation)

    async def activate_allocation(
        self,
        principal: AuthPrincipal,
        allocation_id: UUID,
        payload: ActivateWorkAllocationRequest,
        *,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> WorkAllocationData:
        self._require_admin(principal)
        allocation = await self._session.scalar(
            select(WorkAllocation)
            .where(WorkAllocation.id == allocation_id)
            .with_for_update()
        )
        if allocation is None:
            raise DomainError(
                code="WORK_ALLOCATION_NOT_FOUND",
                message="Work allocation was not found.",
                status_code=404,
            )
        if allocation.status is not WorkAllocationStatus.DRAFT:
            raise DomainError(
                code="WORK_ALLOCATION_STATE_INVALID",
                message="Only a draft work allocation can be activated.",
                status_code=409,
            )
        active_member_ids = set(
            (
                await self._session.scalars(
                    select(AllocationMember.user_id).where(
                        AllocationMember.allocation_id == allocation.id,
                        AllocationMember.is_active.is_(True),
                    )
                )
            ).all()
        )
        await self._validate_member_ids(active_member_ids)

        scopes = tuple(
            (
                await self._session.scalars(
                    select(WorkScope).where(WorkScope.allocation_id == allocation.id)
                )
            ).all()
        )
        coverage_by_scope = {
            coverage.scope_id: coverage.review_assignment_ids
            for coverage in payload.scope_coverage
        }
        if allocation.kind is WorkAllocationKind.GENERIC:
            if scopes or coverage_by_scope:
                raise self._incomplete_coverage()
            return await self._activate(
                allocation,
                principal,
                audit=audit,
                request_id=request_id,
                user_agent=user_agent,
                scope_count=0,
                review_assignment_count=0,
            )
        if not scopes or set(coverage_by_scope) != {scope.id for scope in scopes}:
            raise self._incomplete_coverage()

        assignment_ids = {
            assignment_id
            for assignment_group in coverage_by_scope.values()
            for assignment_id in assignment_group
        }
        assignments = {
            assignment.id: assignment
            for assignment in (
                await self._session.scalars(
                    select(ReviewAssignment).where(
                        ReviewAssignment.id.in_(assignment_ids)
                    )
                )
            ).all()
        }
        if len(assignments) != len(assignment_ids):
            raise self._incomplete_coverage()
        reviewer_members = {
            member.user_id: member
            for member in (
                await self._session.scalars(
                    select(AllocationMember).where(
                        AllocationMember.allocation_id == allocation.id,
                        AllocationMember.is_active.is_(True),
                        AllocationMember.responsibility
                        == AllocationResponsibility.REVIEWER,
                    )
                )
            ).all()
        }
        scope_assignment_links: list[WorkScopeReviewAssignment] = []
        for scope in scopes:
            scope_assignments = [
                assignments[assignment_id]
                for assignment_id in coverage_by_scope[scope.id]
            ]
            reviewer_ids = {
                assignment.reviewer_user_id for assignment in scope_assignments
            }
            required_reviewers = 2 if scope.requires_dual_review else 1
            if len(reviewer_ids) < required_reviewers or any(
                not self._is_valid_scope_assignment(
                    allocation,
                    assignment,
                    reviewer_members,
                )
                for assignment in scope_assignments
            ):
                raise self._incomplete_coverage()
            scope_assignment_links.extend(
                WorkScopeReviewAssignment(
                    scope_id=scope.id,
                    allocation_member_id=reviewer_members[
                        assignment.reviewer_user_id
                    ].id,
                    review_assignment_id=assignment.id,
                )
                for assignment in scope_assignments
            )
        self._session.add_all(scope_assignment_links)
        return await self._activate(
            allocation,
            principal,
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
            scope_count=len(scopes),
            review_assignment_count=len(scope_assignment_links),
        )

    async def list_allocations(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[WorkAllocationData, ...], int]:
        self._require_admin(principal)
        total = int(
            await self._session.scalar(select(func.count()).select_from(WorkAllocation))
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(WorkAllocation)
                    .order_by(WorkAllocation.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._data(row) for row in rows), total

    async def get_allocation(
        self,
        principal: AuthPrincipal,
        allocation_id: UUID,
    ) -> WorkAllocationDetailData:
        self._require_admin(principal)
        allocation = await self._session.scalar(
            select(WorkAllocation).where(WorkAllocation.id == allocation_id)
        )
        if allocation is None:
            raise DomainError(
                code="WORK_ALLOCATION_NOT_FOUND",
                message="Work allocation was not found.",
                status_code=404,
            )
        scopes = tuple(
            (
                await self._session.scalars(
                    select(WorkScope)
                    .where(WorkScope.allocation_id == allocation.id)
                    .order_by(WorkScope.created_at, WorkScope.id)
                )
            ).all()
        )
        members = tuple(
            (
                await self._session.scalars(
                    select(AllocationMember)
                    .where(AllocationMember.allocation_id == allocation.id)
                    .order_by(AllocationMember.created_at, AllocationMember.id)
                )
            ).all()
        )
        evidence_ids = {
            scope.dossier_evidence_id
            for scope in scopes
            if scope.dossier_evidence_id is not None
        }
        evidence_titles: dict[UUID, str] = {}
        if evidence_ids:
            evidence_rows = await self._session.execute(
                select(DossierEvidence.id, DossierEvidence.title).where(
                    DossierEvidence.id.in_(evidence_ids)
                )
            )
            evidence_titles = dict(evidence_rows.tuples().all())
        coverage: dict[UUID, dict[str, list[UUID]]] = {
            scope.id: {"review_assignment_ids": [], "reviewer_user_ids": []}
            for scope in scopes
        }
        if coverage:
            rows = await self._session.execute(
                select(
                    WorkScopeReviewAssignment.scope_id,
                    ReviewAssignment.id,
                    ReviewAssignment.reviewer_user_id,
                )
                .join(
                    ReviewAssignment,
                    ReviewAssignment.id
                    == WorkScopeReviewAssignment.review_assignment_id,
                )
                .where(WorkScopeReviewAssignment.scope_id.in_(coverage))
                .order_by(
                    WorkScopeReviewAssignment.scope_id,
                    WorkScopeReviewAssignment.created_at,
                )
            )
            for scope_id, review_assignment_id, reviewer_user_id in rows.tuples():
                coverage[scope_id]["review_assignment_ids"].append(review_assignment_id)
                coverage[scope_id]["reviewer_user_ids"].append(reviewer_user_id)
        allocation_data = self._data(allocation)
        return WorkAllocationDetailData.model_validate(
            {
                **allocation_data.model_dump(),
                "scopes": [
                    self._scope_data(scope).model_copy(
                        update={
                            "dossier_evidence_title": (
                                evidence_titles.get(scope.dossier_evidence_id)
                                if scope.dossier_evidence_id is not None
                                else None
                            )
                        }
                    )
                    for scope in scopes
                ],
                "members": [self._member_data(member) for member in members],
                "scope_coverage": [
                    WorkScopeCoverageData(
                        scope_id=scope.id,
                        review_assignment_ids=coverage[scope.id][
                            "review_assignment_ids"
                        ],
                        reviewer_user_ids=coverage[scope.id]["reviewer_user_ids"],
                    )
                    for scope in scopes
                ],
            }
        )

    async def list_my_allocations(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[WorkAllocationData, ...], int]:
        self._require_moderator(principal)
        criteria = (
            AllocationMember.user_id == principal.user_id,
            AllocationMember.is_active.is_(True),
        )
        total = int(
            await self._session.scalar(
                select(func.count())
                .select_from(WorkAllocation)
                .join(AllocationMember)
                .where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(WorkAllocation)
                    .join(AllocationMember)
                    .where(*criteria)
                    .order_by(WorkAllocation.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._data(row) for row in rows), total

    async def _validate_members(self, payload: CreateWorkAllocationRequest) -> None:
        await self._validate_member_ids({member.user_id for member in payload.members})

    async def _validate_member_ids(self, member_ids: set[UUID]) -> None:
        if not member_ids:
            return
        existing_ids = set(
            (
                await self._session.scalars(
                    select(User.id).where(User.id.in_(member_ids))
                )
            ).all()
        )
        missing_ids = member_ids - existing_ids
        if missing_ids:
            raise DomainError(
                code="WORK_ALLOCATION_MEMBER_NOT_FOUND",
                message="One or more assigned people do not exist.",
                status_code=422,
                details={"member_ids": sorted(str(value) for value in missing_ids)},
            )
        eligible_ids = set(
            (
                await self._session.scalars(
                    select(User.id)
                    .join(UserRole, UserRole.user_id == User.id)
                    .join(Role, Role.id == UserRole.role_id)
                    .where(
                        User.id.in_(member_ids),
                        User.status == UserStatus.ACTIVE,
                        Role.code == "MODERATOR",
                    )
                )
            ).all()
        )
        ineligible_ids = member_ids - eligible_ids
        if ineligible_ids:
            raise DomainError(
                code="WORK_ALLOCATION_MEMBER_INELIGIBLE",
                message="Assigned people must be active moderators.",
                status_code=422,
                details={"member_ids": sorted(str(value) for value in ineligible_ids)},
            )

    @staticmethod
    def _incomplete_coverage() -> DomainError:
        return DomainError(
            code="WORK_ALLOCATION_COVERAGE_INCOMPLETE",
            message=(
                "Every document scope must have the required independent "
                "reviewer coverage before activation."
            ),
            status_code=422,
        )

    def _is_valid_scope_assignment(
        self,
        allocation: WorkAllocation,
        assignment: ReviewAssignment,
        reviewer_members: dict[UUID, AllocationMember],
    ) -> bool:
        return (
            assignment.dossier_id == allocation.dossier_id
            and assignment.dossier_version_id == allocation.dossier_version_id
            and assignment.status in self.COVERAGE_ASSIGNMENT_STATUSES
            and assignment.reviewer_user_id in reviewer_members
        )

    async def _activate(
        self,
        allocation: WorkAllocation,
        principal: AuthPrincipal,
        *,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
        scope_count: int,
        review_assignment_count: int,
    ) -> WorkAllocationData:
        allocation.status = WorkAllocationStatus.ACTIVE
        try:
            await self._session.flush()
            audit.record(
                actor_user_id=principal.user_id,
                action="work.allocation.activated",
                resource_type="work_allocation",
                resource_id=str(allocation.id),
                after={
                    "kind": allocation.kind.value,
                    "status": allocation.status.value,
                    "scope_count": scope_count,
                    "review_assignment_count": review_assignment_count,
                },
                request_id=request_id,
                user_agent=user_agent,
            )
            await self._notify_allocation_members(allocation)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._incomplete_coverage() from exc
        await self._session.refresh(allocation)
        return self._data(allocation)

    async def _notify_allocation_members(self, allocation: WorkAllocation) -> None:
        recipient_query = (
            select(AllocationMember.user_id)
            .join(User, User.id == AllocationMember.user_id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                AllocationMember.allocation_id == allocation.id,
                AllocationMember.is_active.is_(True),
                User.status == UserStatus.ACTIVE,
                User.disabled_at.is_(None),
                User.deleted_at.is_(None),
                Role.code == "MODERATOR",
            )
        )
        if allocation.kind is WorkAllocationKind.DOSSIER_REVIEW:
            covered_reviewer_ids = (
                select(AllocationMember.user_id)
                .join(
                    WorkScopeReviewAssignment,
                    WorkScopeReviewAssignment.allocation_member_id
                    == AllocationMember.id,
                )
                .join(
                    WorkScope,
                    WorkScope.id == WorkScopeReviewAssignment.scope_id,
                )
                .where(
                    WorkScope.allocation_id == allocation.id,
                    WorkScopeReviewAssignment.review_assignment_id.is_not(None),
                )
            )
            recipient_query = recipient_query.where(
                AllocationMember.user_id.not_in(covered_reviewer_ids)
            )

        event_id = uuid5(NAMESPACE_URL, f"work.allocation.activated:{allocation.id}")
        for user_id in set((await self._session.scalars(recipient_query)).all()):
            self._session.add(
                Notification(
                    user_id=user_id,
                    source_event_id=event_id,
                    type="WORK_ALLOCATION_ASSIGNED",
                    title="Phân công công việc mới",
                    body="Bạn có công việc mới cần thực hiện.",
                    data_json={"actionPath": "/work-allocations"},
                    created_at=datetime.now(UTC),
                )
            )
        await self._session.flush()

    async def _validate_dossier_scopes(
        self, payload: CreateWorkAllocationRequest
    ) -> None:
        if payload.kind is WorkAllocationKind.GENERIC:
            return
        version = await self._session.scalar(
            select(DossierVersion).where(
                DossierVersion.id == payload.dossier_version_id,
                DossierVersion.dossier_id == payload.dossier_id,
            )
        )
        if version is None:
            raise DomainError(
                code="WORK_ALLOCATION_DOSSIER_VERSION_NOT_FOUND",
                message="The selected dossier version does not belong to this dossier.",
                status_code=422,
            )
        evidence_ids = {
            scope.dossier_evidence_id
            for scope in payload.scopes
            if scope.dossier_evidence_id is not None
        }
        if not evidence_ids:
            return
        valid_evidence_ids = set(
            (
                await self._session.scalars(
                    select(DossierEvidence.id).where(
                        DossierEvidence.id.in_(evidence_ids),
                        DossierEvidence.dossier_id == payload.dossier_id,
                        DossierEvidence.dossier_version_id
                        == payload.dossier_version_id,
                    )
                )
            ).all()
        )
        missing_ids = evidence_ids - valid_evidence_ids
        if missing_ids:
            raise DomainError(
                code="WORK_ALLOCATION_SCOPE_NOT_FOUND",
                message=(
                    "One or more selected documents are unavailable in this version."
                ),
                status_code=422,
                details={"evidence_ids": sorted(str(value) for value in missing_ids)},
            )
