import asyncio
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import (
    AttendanceAssignment,
    AttendanceWorksite,
    AttendanceWorksitePolicy,
    AttendanceWorksiteStatus,
    Department,
    Employee,
)
from app.modules.hr.schemas import (
    CreateAttendanceAssignmentRequest,
    CreateAttendanceWorksitePolicyRequest,
    CreateAttendanceWorksiteRequest,
    UpdateAttendanceWorksiteRequest,
)
from app.modules.hr.service import HrService


async def _create_global_attendance_tables(engine: object) -> None:
    async with engine.begin() as connection:  # type: ignore[union-attr]
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[
                    User.__table__,
                    Department.__table__,
                    Employee.__table__,
                    AttendanceWorksite.__table__,
                    AttendanceWorksitePolicy.__table__,
                    AttendanceAssignment.__table__,
                    AuditLog.__table__,
                ],
            )
        )


def _principal(
    *, roles: tuple[str, ...] = (), permissions: tuple[str, ...] = ()
) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="attendance-admin@example.com",
        roles=roles,
        permissions=permissions,
    )


def _policy_request(*, effective_from: date) -> CreateAttendanceWorksitePolicyRequest:
    return CreateAttendanceWorksitePolicyRequest(
        effective_from=effective_from,
        timezone="America/New_York",
        latitude=Decimal("40.712800"),
        longitude=Decimal("-74.006000"),
        radius_meters=250,
        max_accuracy_meters=40,
    )


def test_super_admin_manages_append_only_worksite_policy_and_assignment() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_global_attendance_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="OPS", name="Operations")
            session.add(department)
            await session.flush()
            employee = Employee(
                employee_code="OPS-001",
                full_name="Avery Patel",
                email="avery@example.com",
                department_id=department.id,
                position="Field reviewer",
                join_date=date(2026, 9, 1),
            )
            session.add(employee)
            await session.flush()
            employee_id = employee.id

        async with sessions() as session:
            service = HrService(session)
            worksite = await service.create_attendance_worksite(
                admin,
                CreateAttendanceWorksiteRequest(code="nyc-hq", name="New York HQ"),
                audit=AuditService(session),
                request_id="global-attendance-admin",
                user_agent="pytest",
            )
            policy = await service.create_attendance_worksite_policy(
                admin,
                worksite.id,
                _policy_request(effective_from=date(2026, 9, 1)),
                audit=AuditService(session),
                request_id="global-attendance-admin",
                user_agent="pytest",
            )
            assignment = await service.create_attendance_assignment(
                admin,
                CreateAttendanceAssignmentRequest(
                    employee_id=employee_id,
                    worksite_id=worksite.id,
                    effective_from=date(2026, 9, 1),
                    schedule_code="MON_FRI_8H",
                    holiday_calendar_code="US-NY",
                ),
                audit=AuditService(session),
                request_id="global-attendance-admin",
                user_agent="pytest",
            )

            assert worksite.code == "NYC-HQ"
            assert policy.timezone == "America/New_York"
            assert assignment.employee_name == "Avery Patel"
            assert assignment.worksite_code == "NYC-HQ"

            worksites, total = await service.list_attendance_worksites(
                admin, page=1, page_size=20, search="York", worksite_status=None
            )
            policies, policy_total = await service.list_attendance_worksite_policies(
                admin, worksite.id, page=1, page_size=20
            )
            assignments, assignment_total = await service.list_attendance_assignments(
                admin, page=1, page_size=20, employee_id=employee_id, worksite_id=None
            )
            assert total == policy_total == assignment_total == 1
            assert worksites[0].id == worksite.id
            assert policies[0].id == policy.id
            assert assignments[0].id == assignment.id

            audit_rows = tuple(
                (
                    await session.scalars(
                        select(AuditLog).where(
                            AuditLog.action.in_(
                                [
                                    "hr.attendance_worksite.created",
                                    "hr.attendance_worksite_policy.created",
                                    "hr.attendance_assignment.created",
                                ]
                            )
                        )
                    )
                ).all()
            )
            assert len(audit_rows) == 3
            assert all("latitude" not in row.after_json for row in audit_rows)
            assert all("longitude" not in row.after_json for row in audit_rows)
        await engine.dispose()

    asyncio.run(exercise())


def test_global_attendance_admin_rejects_overlap_inactive_worksite_and_user_role() -> (
    None
):
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_global_attendance_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="OPS", name="Operations")
            session.add(department)
            await session.flush()
            employee = Employee(
                employee_code="OPS-002",
                full_name="Jordan Nguyen",
                email="jordan@example.com",
                department_id=department.id,
                position="Reviewer",
                join_date=date(2026, 9, 1),
            )
            session.add(employee)
            await session.flush()
            employee_id = employee.id

        async with sessions() as session:
            service = HrService(session)
            worksite = await service.create_attendance_worksite(
                admin,
                CreateAttendanceWorksiteRequest(code="lhr", name="London Hub"),
                audit=AuditService(session),
                request_id="global-attendance-overlap",
                user_agent="pytest",
            )
            await service.create_attendance_worksite_policy(
                admin,
                worksite.id,
                CreateAttendanceWorksitePolicyRequest(
                    effective_from=date(2026, 9, 1),
                    timezone="Europe/London",
                    latitude=Decimal("51.507400"),
                    longitude=Decimal("-0.127800"),
                    radius_meters=120,
                    max_accuracy_meters=30,
                ),
                audit=AuditService(session),
                request_id="global-attendance-overlap",
                user_agent="pytest",
            )
            with pytest.raises(DomainError) as policy_overlap:
                await service.create_attendance_worksite_policy(
                    admin,
                    worksite.id,
                    _policy_request(effective_from=date(2026, 10, 1)),
                    audit=AuditService(session),
                    request_id="global-attendance-overlap",
                    user_agent="pytest",
                )
            assert policy_overlap.value.code == "HR_ATTENDANCE_POLICY_OVERLAP"

            await service.create_attendance_assignment(
                admin,
                CreateAttendanceAssignmentRequest(
                    employee_id=employee_id,
                    worksite_id=worksite.id,
                    effective_from=date(2026, 9, 1),
                    schedule_code="MON_FRI_8H",
                    holiday_calendar_code="GB-ENG",
                ),
                audit=AuditService(session),
                request_id="global-attendance-overlap",
                user_agent="pytest",
            )
            with pytest.raises(DomainError) as assignment_overlap:
                await service.create_attendance_assignment(
                    admin,
                    CreateAttendanceAssignmentRequest(
                        employee_id=employee_id,
                        worksite_id=worksite.id,
                        effective_from=date(2026, 10, 1),
                        schedule_code="MON_FRI_8H",
                        holiday_calendar_code="GB-ENG",
                    ),
                    audit=AuditService(session),
                    request_id="global-attendance-overlap",
                    user_agent="pytest",
                )
            assert assignment_overlap.value.code == "HR_ATTENDANCE_ASSIGNMENT_OVERLAP"

            updated = await service.update_attendance_worksite(
                admin,
                worksite.id,
                UpdateAttendanceWorksiteRequest(
                    status=AttendanceWorksiteStatus.INACTIVE
                ),
                audit=AuditService(session),
                request_id="global-attendance-overlap",
                user_agent="pytest",
            )
            assert updated.status == AttendanceWorksiteStatus.INACTIVE
            with pytest.raises(DomainError) as inactive:
                await service.create_attendance_worksite_policy(
                    admin,
                    worksite.id,
                    _policy_request(effective_from=date(2026, 12, 1)),
                    audit=AuditService(session),
                    request_id="global-attendance-overlap",
                    user_agent="pytest",
                )
            assert inactive.value.code == "HR_ATTENDANCE_WORKSITE_INACTIVE"

            with pytest.raises(DomainError) as denied:
                await service.list_attendance_worksites(
                    _principal(
                        roles=("MODERATOR",),
                        permissions=("hr.attendance.worksites.read",),
                    ),
                    page=1,
                    page_size=20,
                    search=None,
                    worksite_status=None,
                )
            assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())


def test_global_attendance_policy_rejects_unknown_iana_timezone() -> None:
    with pytest.raises(ValueError):
        CreateAttendanceWorksitePolicyRequest(
            effective_from=date(2026, 9, 1),
            timezone="Mars/Olympus_Mons",
            latitude=Decimal("0"),
            longitude=Decimal("0"),
            radius_meters=100,
            max_accuracy_meters=25,
        )
