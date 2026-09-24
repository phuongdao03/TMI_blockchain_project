import asyncio
from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import Department, Employee, LeaveRequest, OvertimeRequest
from app.modules.hr.schemas import CreateLeaveRequest, CreateOvertimeRequest
from app.modules.hr.service import HrService
from app.modules.notifications.models import Notification
from app.modules.notifications.redaction import redact_notification_data
from app.modules.notifications.service import NotificationService
from app.tests.test_hr_service import _create_hr_tables


async def seed_recipients(
    session: AsyncSession, *, with_admins: bool
) -> tuple[AuthPrincipal, set[UUID]]:
    roles = {
        code: Role(code=code) for code in ("SUPER_ADMIN", "MODERATOR", "USER", "VIEWER")
    }
    session.add_all(roles.values())
    moderator = User(email="employee@example.com", status=UserStatus.ACTIVE)
    session.add(moderator)
    department = Department(code="OPS", name="Operations")
    session.add(department)
    await session.flush()
    session.add(UserRole(user_id=moderator.id, role_id=roles["MODERATOR"].id))
    session.add(
        Employee(
            employee_code="EMP-1",
            user_id=moderator.id,
            full_name="Private employee",
            email=moderator.email,
            department_id=department.id,
            position="Reviewer",
            join_date=date(2026, 1, 1),
        )
    )
    eligible: set[UUID] = set()
    if with_admins:
        for index, (role, status, disabled, deleted) in enumerate(
            [
                ("SUPER_ADMIN", UserStatus.ACTIVE, False, False),
                ("SUPER_ADMIN", UserStatus.ACTIVE, False, False),
                ("SUPER_ADMIN", UserStatus.SUSPENDED, False, False),
                ("SUPER_ADMIN", UserStatus.PENDING, False, False),
                ("SUPER_ADMIN", UserStatus.DELETED, False, False),
                ("SUPER_ADMIN", UserStatus.ACTIVE, True, False),
                ("SUPER_ADMIN", UserStatus.ACTIVE, False, True),
                ("USER", UserStatus.ACTIVE, False, False),
                ("VIEWER", UserStatus.ACTIVE, False, False),
            ]
        ):
            user = User(
                email=f"recipient-{index}@example.com",
                status=status,
                disabled_at=datetime(2026, 1, 1, tzinfo=UTC) if disabled else None,
                deleted_at=datetime(2026, 1, 1, tzinfo=UTC) if deleted else None,
            )
            session.add(user)
            await session.flush()
            session.add(UserRole(user_id=user.id, role_id=roles[role].id))
            if index < 2:
                eligible.add(user.id)
                # Multiple roles must not duplicate the Super Admin notice.
                session.add(UserRole(user_id=user.id, role_id=roles["MODERATOR"].id))
    await session.commit()
    return AuthPrincipal(
        user_id=moderator.id,
        session_id=uuid4(),
        email=moderator.email,
        roles=("MODERATOR",),
        permissions=(),
    ), eligible


async def submit(session: AsyncSession, principal: AuthPrincipal, kind: str) -> UUID:
    service = HrService(session)
    if kind == "leave":
        result = await service.create_leave_request(
            principal,
            CreateLeaveRequest(
                leave_type="Private leave category",
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 2),
                reason="Confidential medical details",
            ),
            audit=AuditService(session),
            request_id="d03a-test",
            user_agent="pytest",
        )
        return result.id
    overtime = await service.create_overtime_request(
        principal,
        CreateOvertimeRequest(
            start_at=datetime(2026, 10, 1, 12, tzinfo=UTC),
            end_at=datetime(2026, 10, 1, 14, tzinfo=UTC),
            reason="Confidential project details",
        ),
        audit=AuditService(session),
        request_id="d03a-test",
        user_agent="pytest",
    )
    return overtime.id


@pytest.mark.parametrize("kind", ["leave", "overtime"])
@pytest.mark.parametrize("with_admins", [True, False])
def test_request_notice_recipients_privacy_ownership_and_deduplication(
    kind: str, with_admins: bool
) -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            principal, eligible = await seed_recipients(
                session, with_admins=with_admins
            )
            request_id = await submit(session, principal, kind)
            notices = tuple((await session.scalars(select(Notification))).all())
            assert {notice.user_id for notice in notices} == eligible
            assert len(notices) == len(eligible)
            key = "leaveRequestId" if kind == "leave" else "overtimeRequestId"
            for notice in notices:
                assert notice.type == f"HR_{kind.upper()}_REQUEST_CREATED"
                assert notice.source_event_id == uuid5(
                    NAMESPACE_URL, f"hr.{kind}.created:{request_id}"
                )
                assert notice.data_json == {
                    key: str(request_id),
                    "actionPath": f"/admin/{kind}",
                }
                assert redact_notification_data(notice.data_json) == notice.data_json
                assert "Private" not in notice.title + notice.body
                assert "Confidential" not in notice.title + notice.body
                assert notice.read_at is None
            request = (
                await session.get(LeaveRequest, request_id)
                if kind == "leave"
                else await session.get(OvertimeRequest, request_id)
            )
            assert request is not None
            await HrService(session)._notify_super_admins_of_hr_request(request)
            await HrService(session)._notify_super_admins_of_hr_request(request)
            await session.commit()
            assert await session.scalar(
                select(func.count()).select_from(Notification)
            ) == len(eligible)
        async with sessions() as session:
            notices, total = await NotificationService(session).list(
                principal.user_id,
                page=1,
                page_size=20,
            )
            assert total == 0
            assert not notices
            for user_id in eligible:
                notices, total = await NotificationService(session).list(
                    user_id,
                    page=1,
                    page_size=20,
                )
                assert total == 1
                assert notices[0].data_json[key] == str(request_id)
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["leave", "overtime"])
def test_failed_request_transaction_leaves_no_request_audit_or_notification(
    kind: str,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            principal, _ = await seed_recipients(session, with_admins=True)

            def fail_commit(sync_session: Session) -> None:
                assert (
                    sync_session.scalar(select(func.count()).select_from(Notification))
                    == 2
                )
                raise RuntimeError("Simulated commit failure")

            event.listen(session.sync_session, "before_commit", fail_commit, once=True)
            with pytest.raises(RuntimeError, match="Simulated commit failure"):
                await submit(session, principal, kind)
            await session.rollback()
        async with sessions() as session:
            for model in (LeaveRequest, OvertimeRequest, AuditLog, Notification):
                assert (
                    await session.scalar(select(func.count()).select_from(model)) == 0
                )
        await engine.dispose()

    asyncio.run(exercise())
