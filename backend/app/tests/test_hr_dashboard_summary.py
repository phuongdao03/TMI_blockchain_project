import asyncio
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.auth.models import User
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.dashboard_service import HrDashboardService
from app.modules.hr.models import (
    Attendance,
    AttendanceAssignment,
    AttendanceLocationEventType,
    AttendanceLocationEvidence,
    AttendanceLocationException,
    AttendanceLocationExceptionStatus,
    AttendanceLocationOutcome,
    AttendanceStatus,
    AttendanceWorksite,
    AttendanceWorksitePolicy,
    Department,
    Employee,
    EmploymentStatus,
    LeaveRequest,
    LeaveRequestStatus,
    OvertimeRequest,
    OvertimeRequestStatus,
    PayrollPeriod,
    PayrollPeriodStatus,
)
from app.modules.hr.service import HrService


async def _create_dashboard_tables(engine: object) -> None:
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
                    Attendance.__table__,
                    AttendanceLocationEvidence.__table__,
                    AttendanceLocationException.__table__,
                    LeaveRequest.__table__,
                    OvertimeRequest.__table__,
                    PayrollPeriod.__table__,
                ],
            )
        )


def _principal(*, roles: tuple[str, ...] = ()) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="dashboard.admin@example.com",
        roles=roles,
        permissions=(),
    )


def test_dashboard_summary_returns_only_super_admin_aggregate_queues() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_dashboard_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        now = datetime(2026, 9, 23, 8, tzinfo=UTC)

        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="OPS", name="Operations")
            worksite = AttendanceWorksite(code="SGN-HQ", name="Ho Chi Minh office")
            session.add_all([department, worksite])
            await session.flush()
            active_employee = Employee(
                employee_code="NV-001",
                full_name="Nguyen Minh An",
                email="an@example.com",
                department_id=department.id,
                position="Operations specialist",
                join_date=date(2026, 1, 1),
                employment_status=EmploymentStatus.ACTIVE,
            )
            inactive_employee = Employee(
                employee_code="NV-002",
                full_name="Le Thu Ha",
                email="ha@example.com",
                department_id=department.id,
                position="Operations specialist",
                join_date=date(2026, 1, 1),
                employment_status=EmploymentStatus.INACTIVE,
            )
            session.add_all([active_employee, inactive_employee])
            await session.flush()
            policy = AttendanceWorksitePolicy(
                worksite_id=worksite.id,
                effective_from=date(2026, 1, 1),
                timezone="Asia/Ho_Chi_Minh",
                latitude=Decimal("10.776900"),
                longitude=Decimal("106.700900"),
                radius_meters=100,
                max_accuracy_meters=50,
            )
            pending_attendance = Attendance(
                employee_id=active_employee.id,
                work_date=date(2026, 9, 22),
                status=AttendanceStatus.PENDING,
            )
            session.add_all(
                [
                    policy,
                    pending_attendance,
                    Attendance(
                        employee_id=active_employee.id,
                        work_date=date(2026, 9, 21),
                        status=AttendanceStatus.PRESENT,
                    ),
                    LeaveRequest(
                        employee_id=active_employee.id,
                        leave_type="ANNUAL",
                        start_date=date(2026, 9, 24),
                        end_date=date(2026, 9, 24),
                        reason="Personal leave",
                        status=LeaveRequestStatus.PENDING,
                    ),
                    LeaveRequest(
                        employee_id=active_employee.id,
                        leave_type="ANNUAL",
                        start_date=date(2026, 9, 25),
                        end_date=date(2026, 9, 25),
                        reason="Approved leave",
                        status=LeaveRequestStatus.APPROVED,
                    ),
                    OvertimeRequest(
                        employee_id=active_employee.id,
                        start_at=now,
                        end_at=datetime(2026, 9, 23, 10, tzinfo=UTC),
                        reason="Pending overtime",
                        status=OvertimeRequestStatus.PENDING,
                    ),
                    OvertimeRequest(
                        employee_id=active_employee.id,
                        start_at=datetime(2026, 9, 22, 8, tzinfo=UTC),
                        end_at=datetime(2026, 9, 22, 10, tzinfo=UTC),
                        reason="Approved overtime",
                        status=OvertimeRequestStatus.APPROVED,
                    ),
                    PayrollPeriod(
                        worksite_id=worksite.id,
                        period_month=date(2026, 9, 1),
                        standard_workdays=22,
                        status=PayrollPeriodStatus.DRAFT,
                    ),
                    PayrollPeriod(
                        worksite_id=worksite.id,
                        period_month=date(2026, 8, 1),
                        standard_workdays=22,
                        status=PayrollPeriodStatus.CONFIRMED,
                    ),
                ]
            )
            await session.flush()
            evidence = AttendanceLocationEvidence(
                attendance_id=pending_attendance.id,
                event_type=AttendanceLocationEventType.CHECK_IN,
                worksite_policy_id=policy.id,
                client_captured_at=now,
                latitude=Decimal("10.776900"),
                longitude=Decimal("106.700900"),
                accuracy_meters=Decimal("20"),
                distance_meters=Decimal("150"),
                effective_timezone="Asia/Ho_Chi_Minh",
                permitted_radius_meters=100,
                max_accuracy_meters=50,
                outcome=AttendanceLocationOutcome.OUTSIDE_WORKSITE,
                retention_until=datetime(2028, 9, 23, tzinfo=UTC),
            )
            session.add(evidence)
            await session.flush()
            session.add(
                AttendanceLocationException(
                    attendance_id=pending_attendance.id,
                    location_evidence_id=evidence.id,
                    status=AttendanceLocationExceptionStatus.PENDING,
                    requested_by_user_id=admin.user_id,
                    decision_note="Do not expose this reason in the dashboard.",
                )
            )

        async with sessions() as session:
            summary = await HrDashboardService(session).summary(admin)
            assert asdict(summary) == {
                "active_employee_count": 1,
                "attendance_pending_count": 1,
                "location_exception_pending_count": 1,
                "leave_pending_count": 1,
                "overtime_pending_count": 1,
                "payroll_draft_count": 1,
                "updated_at": summary.updated_at,
            }
            assert summary.updated_at.tzinfo is not None
            assert set(asdict(summary)) == {
                "active_employee_count",
                "attendance_pending_count",
                "location_exception_pending_count",
                "leave_pending_count",
                "overtime_pending_count",
                "payroll_draft_count",
                "updated_at",
            }

        await engine.dispose()

    asyncio.run(exercise())


def test_dashboard_summary_requires_super_admin() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_dashboard_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            with pytest.raises(DomainError) as denied:
                await HrDashboardService(session).summary(
                    _principal(roles=("MODERATOR",))
                )
            assert denied.value.code == "HR_DASHBOARD_FORBIDDEN"
            assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())


def test_moderator_summary_returns_only_their_personal_hr_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_dashboard_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(roles=("MODERATOR",))
        now = datetime(2026, 9, 23, 23, 30, tzinfo=UTC)
        monkeypatch.setattr(HrService, "_now", staticmethod(lambda: now))
        local_date = now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()

        async with sessions.begin() as session:
            session.add(
                User(id=moderator.user_id, email=moderator.email, password_hash=None)
            )
            department = Department(code="REV", name="Review")
            worksite = AttendanceWorksite(code="SGN-REV", name="Review office")
            session.add_all([department, worksite])
            await session.flush()
            employee = Employee(
                employee_code="RV-001",
                user_id=moderator.user_id,
                full_name="Moderator One",
                email=moderator.email,
                department_id=department.id,
                position="Reviewer",
                join_date=date(2020, 1, 1),
                employment_status=EmploymentStatus.ACTIVE,
            )
            other_employee = Employee(
                employee_code="RV-002",
                full_name="Moderator Two",
                email="other@example.com",
                department_id=department.id,
                position="Reviewer",
                join_date=date(2020, 1, 1),
                employment_status=EmploymentStatus.ACTIVE,
            )
            session.add_all([employee, other_employee])
            await session.flush()
            session.add_all(
                [
                    AttendanceWorksitePolicy(
                        worksite_id=worksite.id,
                        effective_from=date(2020, 1, 1),
                        timezone="Asia/Ho_Chi_Minh",
                        latitude=Decimal("10.776900"),
                        longitude=Decimal("106.700900"),
                        radius_meters=100,
                        max_accuracy_meters=50,
                    ),
                    AttendanceAssignment(
                        employee_id=employee.id,
                        worksite_id=worksite.id,
                        effective_from=date(2020, 1, 1),
                        schedule_code="MON_FRI_8H",
                        holiday_calendar_code="VN-HCM",
                    ),
                    Attendance(
                        employee_id=employee.id,
                        work_date=local_date,
                        check_in_at=now,
                        status=AttendanceStatus.PENDING,
                    ),
                    LeaveRequest(
                        employee_id=employee.id,
                        leave_type="ANNUAL",
                        start_date=local_date,
                        end_date=local_date,
                        reason="Personal leave",
                        status=LeaveRequestStatus.PENDING,
                    ),
                    LeaveRequest(
                        employee_id=other_employee.id,
                        leave_type="ANNUAL",
                        start_date=local_date,
                        end_date=local_date,
                        reason="Other employee leave",
                        status=LeaveRequestStatus.PENDING,
                    ),
                    OvertimeRequest(
                        employee_id=employee.id,
                        start_at=now,
                        end_at=now + timedelta(hours=1),
                        reason="Personal overtime",
                        status=OvertimeRequestStatus.PENDING,
                    ),
                    OvertimeRequest(
                        employee_id=other_employee.id,
                        start_at=now,
                        end_at=now + timedelta(hours=1),
                        reason="Other employee overtime",
                        status=OvertimeRequestStatus.PENDING,
                    ),
                ]
            )

        async with sessions() as session:
            summary = await HrDashboardService(session).moderator_summary(moderator)
            assert summary.profile_linked is True
            assert summary.work_date == local_date
            assert summary.work_date == date(2026, 9, 24)
            assert summary.timezone == "Asia/Ho_Chi_Minh"
            assert summary.attendance_status == AttendanceStatus.PENDING
            assert summary.check_in_at is not None
            assert summary.check_out_at is None
            assert summary.leave_pending_count == 1
            assert summary.overtime_pending_count == 1
            assert set(asdict(summary)) == {
                "profile_linked",
                "work_date",
                "timezone",
                "attendance_status",
                "check_in_at",
                "check_out_at",
                "leave_pending_count",
                "overtime_pending_count",
                "updated_at",
            }

            # An expired assignment must not silently become the UTC workday.
            assignment = await session.scalar(
                select(AttendanceAssignment).where(
                    AttendanceAssignment.employee_id == employee.id
                )
            )
            assert assignment is not None
            assignment.effective_to = date(2026, 9, 22)
            await session.flush()
            unconfigured = await HrDashboardService(session).moderator_summary(
                moderator
            )
            assert unconfigured.profile_linked is True
            assert unconfigured.work_date is None
            assert unconfigured.timezone is None
            assert unconfigured.attendance_status is None
            assert unconfigured.check_in_at is None
            assert unconfigured.leave_pending_count == 1

        await engine.dispose()

    asyncio.run(exercise())


def test_moderator_summary_handles_unlinked_profile_and_rejects_other_roles() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_dashboard_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            unlinked = await HrDashboardService(session).moderator_summary(
                _principal(roles=("MODERATOR",))
            )
            assert unlinked.profile_linked is False
            assert unlinked.work_date is None
            assert unlinked.attendance_status is None
            assert unlinked.leave_pending_count == 0
            assert unlinked.overtime_pending_count == 0
            for role in ("VIEWER", "USER", "SUPER_ADMIN"):
                with pytest.raises(DomainError) as denied:
                    await HrDashboardService(session).moderator_summary(
                        _principal(roles=(role,))
                    )
                assert denied.value.code == "HR_MODERATOR_DASHBOARD_FORBIDDEN"
                assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())
