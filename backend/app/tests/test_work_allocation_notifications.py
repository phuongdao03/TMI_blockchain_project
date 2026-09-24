import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from sqlalchemy import Table, event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.notifications.models import Notification
from app.modules.notifications.redaction import redact_notification_data
from app.modules.reviews.models import ReviewAssignment
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
from app.modules.work_allocations.schemas import (
    ActivateWorkAllocationRequest,
    CreateWorkAllocationRequest,
)
from app.modules.work_allocations.service import WorkAllocationService
from app.tests.test_work_allocation_service import _principal


async def seed(
    session: AsyncSession,
    kind: WorkAllocationKind,
) -> tuple[UUID, UUID, set[UUID], ActivateWorkAllocationRequest]:
    admin = User(email="admin@example.com", status=UserStatus.ACTIVE)
    role = Role(code="MODERATOR")
    session.add_all([admin, role])
    await session.flush()
    members = []
    users = []
    for index in range(7):
        user = User(email=f"member-{index}@example.com", status=UserStatus.ACTIVE)
        if index == 4:
            user.disabled_at = datetime(2026, 1, 1, tzinfo=UTC)
        if index == 5:
            user.deleted_at = datetime(2026, 1, 1, tzinfo=UTC)
        session.add(user)
        await session.flush()
        users.append(user)
        session.add(UserRole(user_id=user.id, role_id=role.id))
        if index < 6:
            members.append(
                {
                    "userId": user.id,
                    "responsibility": "REVIEWER" if index == 2 else "CONTRIBUTOR",
                }
            )
    await session.commit()
    principal = _principal(user_id=admin.id, role="SUPER_ADMIN")
    created = await WorkAllocationService(session).create_allocation(
        principal,
        CreateWorkAllocationRequest.model_validate(
            {
                "kind": "GENERIC",
                "objective": "Private document title",
                "description": "Confidential details",
                "members": members,
            }
        ),
        audit=AuditService(session),
        request_id="d03b-create",
        user_agent="pytest",
    )
    allocation = await session.get(WorkAllocation, created.id)
    assert allocation is not None
    rows = list((await session.scalars(select(AllocationMember))).all())
    by_user = {row.user_id: row for row in rows}
    by_user[users[0].id].responsibility = AllocationResponsibility.LEAD
    by_user[users[3].id].is_active = False
    by_user[users[3].id].deactivated_at = datetime(2026, 1, 1, tzinfo=UTC)
    coverage: list[dict[str, object]] = []
    recipients = {user.id for user in users[:3]}
    if kind == WorkAllocationKind.DOSSIER_REVIEW:
        allocation.kind = kind
        allocation.dossier_id = uuid4()
        allocation.dossier_version_id = uuid4()
        assignment = ReviewAssignment(
            dossier_id=allocation.dossier_id,
            dossier_version_id=allocation.dossier_version_id,
            reviewer_user_id=users[2].id,
            assigned_by=admin.id,
        )
        session.add(assignment)
        await session.flush()
        # Same reviewer covers two documents; no allocation notice for either.
        for label in ("Private legal document", "Private financial document"):
            scope = WorkScope(
                allocation_id=allocation.id,
                scope_type=WorkScopeType.GROUP,
                group_label=label,
            )
            session.add(scope)
            await session.flush()
            coverage.append(
                {"scopeId": scope.id, "reviewAssignmentIds": [assignment.id]}
            )
        recipients.remove(users[2].id)
    await session.commit()
    payload = ActivateWorkAllocationRequest.model_validate({"scopeCoverage": coverage})
    return admin.id, allocation.id, recipients, payload


@pytest.mark.parametrize("kind", list(WorkAllocationKind))
@pytest.mark.parametrize("fail_commit", [False, True])
def test_activation_notifications_are_private_unique_and_transactional(
    kind: WorkAllocationKind,
    fail_commit: bool,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        tables = cast(
            list[Table],
            [
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
            ],
        )
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda conn: Base.metadata.create_all(conn, tables=tables)
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            admin_id, allocation_id, recipients, payload = await seed(session, kind)
            service = WorkAllocationService(session)
            principal = _principal(user_id=admin_id, role="SUPER_ADMIN")
            assert (
                await session.scalar(select(func.count()).select_from(Notification))
                == 0
            )

            async def activate() -> None:
                await service.activate_allocation(
                    principal,
                    allocation_id,
                    payload,
                    audit=AuditService(session),
                    request_id="d03b-activate",
                    user_agent="pytest",
                )

            if fail_commit:

                def fail(sync_session: Session) -> None:
                    assert sync_session.scalar(
                        select(func.count()).select_from(Notification)
                    ) == len(recipients)
                    raise RuntimeError("Simulated commit failure")

                event.listen(session.sync_session, "before_commit", fail, once=True)
                with pytest.raises(RuntimeError, match="Simulated commit failure"):
                    await activate()
                await session.rollback()
            else:
                await activate()
                with pytest.raises(DomainError) as repeat:
                    await activate()
                assert repeat.value.code == "WORK_ALLOCATION_STATE_INVALID"

        async with sessions() as session:
            notices = tuple((await session.scalars(select(Notification))).all())
            assert {notice.user_id for notice in notices} == (
                set() if fail_commit else recipients
            )
            assert len(notices) == (0 if fail_commit else len(recipients))
            for notice in notices:
                assert notice.type == "WORK_ALLOCATION_ASSIGNED"
                assert notice.title == "Phân công công việc mới"
                assert notice.body == "Bạn có công việc mới cần thực hiện."
                assert notice.data_json == {"actionPath": "/work-allocations"}
                assert redact_notification_data(notice.data_json) == notice.data_json
                assert notice.source_event_id == uuid5(
                    NAMESPACE_URL, f"work.allocation.activated:{allocation_id}"
                )
                assert notice.read_at is None
            expected_status = (
                WorkAllocationStatus.DRAFT
                if fail_commit
                else WorkAllocationStatus.ACTIVE
            )
            assert (
                await session.scalar(select(WorkAllocation.status)) == expected_status
            )
            audit_count = await session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "work.allocation.activated")
            )
            assert audit_count == (0 if fail_commit else 1)
            if fail_commit:
                assert (
                    await session.scalar(
                        select(func.count()).select_from(WorkScopeReviewAssignment)
                    )
                    == 0
                )
        await engine.dispose()

    asyncio.run(exercise())
