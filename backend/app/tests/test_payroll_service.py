import asyncio
from datetime import UTC, date, datetime
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
    Attendance,
    AttendanceAssignment,
    AttendanceStatus,
    AttendanceWorksite,
    AttendanceWorksitePolicy,
    Department,
    Employee,
    OvertimeRequest,
    OvertimeRequestStatus,
    PayrollEntry,
    PayrollPeriod,
)
from app.modules.hr.payroll_service import PayrollService
from app.modules.hr.schemas import UpdatePayrollEntryRequest


async def _create_payroll_service_tables(engine: object) -> None:
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
                    OvertimeRequest.__table__,
                    PayrollPeriod.__table__,
                    PayrollEntry.__table__,
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
        email="payroll.admin@example.com",
        roles=roles,
        permissions=permissions,
    )


def test_recalculates_draft_payroll_from_payable_attendance_and_approved_ot() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_payroll_service_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="OPS", name="Operations")
            worksite = AttendanceWorksite(code="SGN-HQ", name="Ho Chi Minh office")
            session.add_all([department, worksite])
            await session.flush()
            employee = Employee(
                employee_code="NV-001",
                full_name="Nguyễn Minh An",
                email="an@example.com",
                department_id=department.id,
                position="Operations specialist",
                join_date=date(2026, 1, 1),
                base_salary=Decimal("18000000"),
            )
            session.add(employee)
            await session.flush()
            session.add(
                AttendanceWorksitePolicy(
                    worksite_id=worksite.id,
                    effective_from=date(2026, 1, 1),
                    timezone="Asia/Ho_Chi_Minh",
                    latitude=Decimal("10.776900"),
                    longitude=Decimal("106.700900"),
                    radius_meters=100,
                    max_accuracy_meters=50,
                )
            )
            session.add(
                AttendanceAssignment(
                    employee_id=employee.id,
                    worksite_id=worksite.id,
                    effective_from=date(2026, 1, 1),
                    schedule_code="MON_FRI_8H",
                    holiday_calendar_code="VN-HCM",
                )
            )
            session.add_all(
                [
                    Attendance(
                        employee_id=employee.id,
                        work_date=date(2026, 9, 1),
                        status=AttendanceStatus.PRESENT,
                    ),
                    Attendance(
                        employee_id=employee.id,
                        work_date=date(2026, 9, 2),
                        status=AttendanceStatus.HALF_DAY,
                    ),
                    Attendance(
                        employee_id=employee.id,
                        work_date=date(2026, 9, 3),
                        status=AttendanceStatus.PENDING,
                    ),
                    OvertimeRequest(
                        employee_id=employee.id,
                        start_at=datetime(2026, 9, 10, 10, tzinfo=UTC),
                        end_at=datetime(2026, 9, 10, 18, tzinfo=UTC),
                        reason="Approved work",
                        status=OvertimeRequestStatus.APPROVED,
                    ),
                    OvertimeRequest(
                        employee_id=employee.id,
                        start_at=datetime(2026, 9, 11, 10, tzinfo=UTC),
                        end_at=datetime(2026, 9, 11, 13, tzinfo=UTC),
                        reason="Pending work",
                        status=OvertimeRequestStatus.PENDING,
                    ),
                ]
            )
            period = PayrollPeriod(
                worksite_id=worksite.id,
                period_month=date(2026, 9, 1),
                standard_workdays=22,
            )
            session.add(period)
            await session.flush()
            period_id = period.id

        async with sessions() as session:
            entries = await PayrollService(session).recalculate_draft_period(
                admin,
                period_id,
                audit=AuditService(session),
                request_id="payroll-test",
                user_agent="pytest",
            )
            assert len(entries) == 1
            entry = entries[0]
            assert entry.attendance_workdays == Decimal("1.50")
            assert entry.approved_overtime_hours == Decimal("8.00")
            assert entry.daily_salary == Decimal("818182")
            assert entry.overtime_salary == Decimal("1227273")
            assert entry.gross_pay == Decimal("2454546")
            assert entry.net_pay == Decimal("2454546")
            adjusted = await PayrollService(session).update_entry(
                admin,
                period_id,
                entry.id,
                UpdatePayrollEntryRequest(allowance=Decimal("2000000")),
                audit=AuditService(session),
                request_id="payroll-test",
                user_agent="pytest",
            )
            assert adjusted.allowance == Decimal("2000000")
            with pytest.raises(DomainError) as incomplete:
                await PayrollService(session).confirm_period(
                    admin,
                    period_id,
                    audit=AuditService(session),
                    request_id="payroll-test",
                    user_agent="pytest",
                )
            assert incomplete.value.code == "HR_PAYROLL_CALCULATION_REQUIRED"
            await PayrollService(session).recalculate_draft_period(
                admin,
                period_id,
                audit=AuditService(session),
                request_id="payroll-test",
                user_agent="pytest",
            )
            confirmed = await PayrollService(session).confirm_period(
                admin,
                period_id,
                audit=AuditService(session),
                request_id="payroll-test",
                user_agent="pytest",
            )
            assert confirmed.status.value == "CONFIRMED"
            paid = await PayrollService(session).mark_period_paid(
                admin,
                period_id,
                audit=AuditService(session),
                request_id="payroll-test",
                user_agent="pytest",
            )
            assert paid.status.value == "PAID"
            with pytest.raises(DomainError) as immutable:
                await PayrollService(session).update_entry(
                    admin,
                    period_id,
                    entry.id,
                    UpdatePayrollEntryRequest(income_tax=Decimal("1")),
                    audit=AuditService(session),
                    request_id="payroll-test",
                    user_agent="pytest",
                )
            assert immutable.value.code == "HR_PAYROLL_PERIOD_NOT_DRAFT"

        async with sessions() as session:
            audit_logs = (
                await session.scalars(
                    select(AuditLog).where(AuditLog.action.like("hr.payroll.%"))
                )
            ).all()
            assert {audit.action for audit in audit_logs} == {
                "hr.payroll.calculated",
                "hr.payroll.entry_adjusted",
                "hr.payroll.confirmed",
                "hr.payroll.paid",
            }
            sensitive_fields = {
                "latitude",
                "longitude",
                "reason",
                "base_salary",
                "daily_salary",
                "overtime_salary",
                "gross_pay",
                "net_pay",
                "allowance",
                "social_insurance",
                "income_tax",
            }
            for audit in audit_logs:
                for snapshot in (audit.before_json, audit.after_json):
                    assert not sensitive_fields.intersection(snapshot or {})
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("role", ("VIEWER", "USER", "MODERATOR"))
def test_recalculate_draft_payroll_requires_super_admin(role: str) -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_payroll_service_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            with pytest.raises(DomainError) as denied:
                await PayrollService(session).recalculate_draft_period(
                    _principal(
                        roles=(role,),
                        permissions=("hr.payroll.read", "hr.payroll.manage"),
                    ),
                    uuid4(),
                    audit=AuditService(session),
                    request_id="payroll-test",
                    user_agent="pytest",
                )
            assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())
