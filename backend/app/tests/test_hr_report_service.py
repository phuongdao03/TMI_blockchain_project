import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4
from zipfile import ZipFile

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import hr as hr_api
from app.core.errors import DomainError
from app.core.health import HealthService
from app.db.base import Base
from app.db.session import get_session
from app.main import create_application
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.models import User
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import (
    Attendance,
    AttendanceStatus,
    Department,
    Employee,
    EmploymentStatus,
    LeaveRequest,
    OvertimeRequest,
)
from app.modules.hr.payroll_service import PayrollService
from app.modules.hr.report_service import HrReportService
from app.modules.tasks.service import TaskService


def _principal(role: str, *, permissions: tuple[str, ...] = ()) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="report-operator@example.test",
        roles=(role,),
        permissions=permissions,
    )


def _strings(content: bytes) -> str:
    with ZipFile(BytesIO(content)) as archive:
        return archive.read("xl/sharedStrings.xml").decode("utf-8")


def _workbook_xml(content: bytes) -> str:
    with ZipFile(BytesIO(content)) as archive:
        return " ".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.startswith("xl/worksheets/") or name == "xl/sharedStrings.xml"
        )


def test_department_and_employee_reports_filter_and_audit_without_salary() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(
                    sync_connection,
                    tables=[
                        User.__table__,
                        Department.__table__,
                        Employee.__table__,
                        AuditLog.__table__,
                    ],
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal("SUPER_ADMIN")
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="ENG", name="Kỹ thuật")
            session.add(department)
            await session.flush()
            department_id = department.id
            session.add(
                Employee(
                    employee_code="NV-001",
                    full_name="Nguyễn Minh An",
                    email="secret@example.test",
                    phone="+84901234567",
                    department_id=department_id,
                    position="Chuyên viên",
                    join_date=date(2026, 1, 1),
                    base_salary=Decimal("27000000"),
                )
            )
        async with sessions() as session:
            service = HrReportService(session)
            departments = await service.departments(
                admin,
                search="ENG",
                audit=AuditService(session),
                request_id="report-test",
                user_agent="pytest",
            )
            employees = await service.employees(
                admin,
                search="Minh",
                department_id=department_id,
                employment_status=EmploymentStatus.ACTIVE,
                audit=AuditService(session),
                request_id="report-test",
                user_agent="pytest",
            )
            assert "Kỹ thuật" in _strings(departments)
            employee_strings = _strings(employees)
            assert "Nguyễn Minh An" in employee_strings
            assert "NV-001" in employee_strings
            assert "secret@example.test" not in employee_strings
            assert "+84901234567" not in employee_strings
            assert "27000000" not in employee_strings
        async with sessions() as session:
            audits = (
                await session.scalars(
                    select(AuditLog).where(AuditLog.action == "hr.report.exported")
                )
            ).all()
            assert {audit.resource_id for audit in audits} == {
                "departments",
                "employees",
            }
            assert all(
                audit.after_json
                == {
                    "report_kind": audit.resource_id,
                    "row_count": 1,
                }
                for audit in audits
            )
        await engine.dispose()

    asyncio.run(exercise())


def test_attendance_leave_and_overtime_exports_omit_private_evidence() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(
                    sync_connection,
                    tables=[
                        User.__table__,
                        Department.__table__,
                        Employee.__table__,
                        Attendance.__table__,
                        LeaveRequest.__table__,
                        OvertimeRequest.__table__,
                        AuditLog.__table__,
                    ],
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal("SUPER_ADMIN")
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="ENG", name="Kỹ thuật")
            session.add(department)
            await session.flush()
            employee = Employee(
                employee_code="NV-001",
                full_name="Nguyễn Minh An",
                email="secret@example.test",
                department_id=department.id,
                position="Chuyên viên",
                join_date=date(2026, 1, 1),
            )
            session.add(employee)
            await session.flush()
            session.add_all(
                [
                    Attendance(
                        employee_id=employee.id,
                        work_date=date(2026, 9, 23),
                        check_in_at=datetime(2026, 9, 23, 1, tzinfo=UTC),
                        status=AttendanceStatus.PRESENT,
                        check_in_latitude=Decimal("10.123456"),
                        check_in_longitude=Decimal("106.654321"),
                        note="private attendance note",
                    ),
                    LeaveRequest(
                        employee_id=employee.id,
                        leave_type="ANNUAL",
                        start_date=date(2026, 9, 24),
                        end_date=date(2026, 9, 24),
                        reason="private leave reason",
                    ),
                    OvertimeRequest(
                        employee_id=employee.id,
                        start_at=datetime(2026, 9, 23, 10, tzinfo=UTC),
                        end_at=datetime(2026, 9, 23, 12, tzinfo=UTC),
                        reason="private overtime reason",
                    ),
                ]
            )
        async with sessions() as session:
            service = HrReportService(session)
            common = {
                "search": "Minh",
                "department_id": department.id,
                "audit": AuditService(session),
                "request_id": "report-test",
                "user_agent": "pytest",
            }
            attendance = await service.attendance(
                admin,
                attendance_status=AttendanceStatus.PRESENT,
                work_date_from=date(2026, 9, 23),
                work_date_to=date(2026, 9, 23),
                **common,
            )
            leave = await service.leave(
                admin,
                leave_status=None,
                start_date_from=None,
                start_date_to=None,
                **common,
            )
            overtime = await service.overtime(
                admin,
                overtime_status=None,
                start_at_from=None,
                start_at_to=None,
                **common,
            )
            for content in (attendance, leave, overtime):
                xml = _workbook_xml(content)
                assert "Nguyễn Minh An" in xml
                assert "secret@example.test" not in xml
                assert "10.123456" not in xml
                assert "106.654321" not in xml
                assert "private attendance note" not in xml
                assert "private leave reason" not in xml
                assert "private overtime reason" not in xml
        async with sessions() as session:
            audits = (
                await session.scalars(
                    select(AuditLog).where(AuditLog.action == "hr.report.exported")
                )
            ).all()
            assert {audit.resource_id for audit in audits} == {
                "attendance",
                "leave",
                "overtime",
            }
            assert all(
                audit.after_json
                == {
                    "report_kind": audit.resource_id,
                    "row_count": 1,
                }
                for audit in audits
            )
        await engine.dispose()

    asyncio.run(exercise())


def test_employee_report_api_returns_private_download_with_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubReports:
        filters: dict[str, object] | None = None

        async def employees(
            self, _principal: AuthPrincipal, **filters: object
        ) -> bytes:
            self.filters = filters
            return b"PK-test-export"

    async def exercise() -> None:
        stub = StubReports()
        principal = _principal("SUPER_ADMIN")
        app = create_application(health_service=HealthService({}))
        monkeypatch.setattr(hr_api, "HrReportService", lambda _session: stub)
        app.dependency_overrides[get_current_principal] = lambda: principal
        app.dependency_overrides[get_session] = lambda: object()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                response = await client.get(
                    "/api/v1/admin/hr/reports/employees.xlsx",
                    params={"search": "Minh", "employmentStatus": "ACTIVE"},
                )
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "hr-employees.xlsx" in response.headers["content-disposition"]
        assert response.content == b"PK-test-export"
        assert stub.filters is not None
        assert stub.filters["search"] == "Minh"
        assert stub.filters["employment_status"] == EmploymentStatus.ACTIVE
        app.dependency_overrides.clear()

    asyncio.run(exercise())


def test_attendance_leave_and_overtime_report_routes_are_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubReports:
        calls: list[tuple[str, dict[str, object]]]

        def __init__(self) -> None:
            self.calls = []

        async def attendance(
            self, _principal: AuthPrincipal, **filters: object
        ) -> bytes:
            self.calls.append(("attendance", filters))
            return b"PK-attendance"

        async def leave(self, _principal: AuthPrincipal, **filters: object) -> bytes:
            self.calls.append(("leave", filters))
            return b"PK-leave"

        async def overtime(self, _principal: AuthPrincipal, **filters: object) -> bytes:
            self.calls.append(("overtime", filters))
            return b"PK-overtime"

    async def exercise() -> None:
        stub = StubReports()
        principal = _principal("SUPER_ADMIN")
        app = create_application(health_service=HealthService({}))
        monkeypatch.setattr(hr_api, "HrReportService", lambda _session: stub)
        app.dependency_overrides[get_current_principal] = lambda: principal
        app.dependency_overrides[get_session] = lambda: object()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                for kind in ("attendance", "leave", "overtime"):
                    response = await client.get(
                        f"/api/v1/admin/hr/reports/{kind}.xlsx",
                        params={"search": "Minh"},
                    )
                    assert response.status_code == 200, response.text
                    assert response.headers["cache-control"] == "no-store"
                    assert response.headers["x-content-type-options"] == "nosniff"
                    assert response.content == f"PK-{kind}".encode()
        assert [kind for kind, _ in stub.calls] == ["attendance", "leave", "overtime"]
        assert all(filters["search"] == "Minh" for _, filters in stub.calls)
        app.dependency_overrides.clear()

    asyncio.run(exercise())


@pytest.mark.parametrize("role", ("VIEWER", "USER", "MODERATOR"))
def test_misassigned_permissions_cannot_export_hr_reports(role: str) -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine)
        principal = _principal(
            role, permissions=("hr.departments.manage", "hr.employees.read")
        )
        async with sessions() as session:
            service = HrReportService(session)
            with pytest.raises(DomainError) as department_error:
                await service.departments(
                    principal,
                    search=None,
                    audit=AuditService(session),
                    request_id="report-test",
                    user_agent="pytest",
                )
            assert department_error.value.code == "HR_FORBIDDEN"
            with pytest.raises(DomainError) as employee_error:
                await service.employees(
                    principal,
                    search=None,
                    department_id=None,
                    employment_status=None,
                    audit=AuditService(session),
                    request_id="report-test",
                    user_agent="pytest",
                )
            assert employee_error.value.code == "HR_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())


def test_task_and_payroll_report_routes_are_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubReports:
        async def tasks(self, _principal: AuthPrincipal, **filters: object) -> bytes:
            assert filters["search"] == "review"
            return b"PK-tasks"

        async def payroll(
            self, _principal: AuthPrincipal, period_id: object, **_kwargs: object
        ) -> bytes:
            assert period_id == target_period
            return b"PK-payroll"

    async def exercise() -> None:
        app = create_application(health_service=HealthService({}))
        monkeypatch.setattr(hr_api, "HrReportService", lambda _session: StubReports())
        app.dependency_overrides[get_current_principal] = lambda: _principal(
            "SUPER_ADMIN"
        )
        app.dependency_overrides[get_session] = lambda: object()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                for path, expected in (
                    ("/api/v1/admin/hr/reports/tasks.xlsx?search=review", b"PK-tasks"),
                    (
                        f"/api/v1/admin/hr/reports/payroll-periods/{target_period}/xlsx",
                        b"PK-payroll",
                    ),
                ):
                    response = await client.get(path)
                    assert response.status_code == 200, response.text
                    assert response.headers["cache-control"] == "no-store"
                    assert response.content == expected
        app.dependency_overrides.clear()

    target_period = uuid4()
    asyncio.run(exercise())


def test_task_and_payroll_workbooks_redact_private_fields_and_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    employee_id = uuid4()

    async def fake_tasks(self: TaskService, *_args: object, **_kwargs: object):
        return (
            (
                SimpleNamespace(
                    title="Review =unsafe",
                    status=SimpleNamespace(value="TODO"),
                    priority=SimpleNamespace(value="NORMAL"),
                    assignee_employee_id=None,
                    due_at=None,
                    completed_at=None,
                    description="private task detail",
                ),
            ),
            1,
        )

    async def fake_period(self: PayrollService, *_args: object):
        return SimpleNamespace(
            calculated_at=datetime(2026, 9, 23, tzinfo=UTC),
            period_month=date(2026, 9, 1),
            status=SimpleNamespace(value="DRAFT"),
            currency="VND",
            worksite_id=uuid4(),
            standard_workdays=22,
            entries=(
                SimpleNamespace(
                    employee_id=employee_id,
                    employee_code="NV-001",
                    employee_name="Nguyen An",
                    attendance_workdays=Decimal("21"),
                    approved_overtime_hours=Decimal("2"),
                    base_salary=Decimal("18000000"),
                    allowance=Decimal("1000000"),
                    social_insurance=Decimal("1500000"),
                    income_tax=Decimal("500000"),
                    daily_salary=Decimal("818182"),
                    overtime_salary=Decimal("300000"),
                    gross_pay=Decimal("19300000"),
                    total_deductions=Decimal("2000000"),
                    net_pay=Decimal("17300000"),
                    private_note="private payroll adjustment",
                ),
            ),
        )

    monkeypatch.setattr(TaskService, "list_tasks", fake_tasks)
    monkeypatch.setattr(PayrollService, "get_period", fake_period)

    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(
                    sync_connection,
                    tables=[
                        User.__table__,
                        Department.__table__,
                        Employee.__table__,
                        Attendance.__table__,
                        AuditLog.__table__,
                    ],
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal("SUPER_ADMIN")
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="ENG", name="Engineering")
            session.add(department)
            await session.flush()
            session.add(
                Employee(
                    id=employee_id,
                    employee_code="NV-001",
                    full_name="Nguyen An",
                    email="payroll@example.test",
                    department_id=department.id,
                    position="Reviewer",
                    join_date=date(2026, 1, 1),
                )
            )
            session.add(
                Attendance(
                    employee_id=employee_id,
                    work_date=date(2026, 9, 23),
                    check_in_at=datetime(2026, 9, 23, 1, tzinfo=UTC),
                    check_out_at=datetime(2026, 9, 23, 9, tzinfo=UTC),
                    status=AttendanceStatus.PRESENT,
                )
            )
        async with sessions() as session:
            service = HrReportService(session)
            common = {
                "audit": AuditService(session),
                "request_id": "report-test",
                "user_agent": "pytest",
            }
            tasks = await service.tasks(
                admin, search="Review", task_status=None, priority=None, **common
            )
            payroll = await service.payroll(admin, uuid4(), **common)
            assert "Review =unsafe" in _workbook_xml(tasks)
            assert "private task detail" not in _workbook_xml(tasks)
            payroll_xml = _workbook_xml(payroll)
            assert "DRAFT" in payroll_xml
            assert "Nguyen An" in payroll_xml
            assert "NV-001" in payroll_xml
            assert "private payroll adjustment" not in payroll_xml
            for workbook in (tasks, payroll):
                with ZipFile(BytesIO(workbook)) as archive:
                    assert not any(
                        "externalLink" in name for name in archive.namelist()
                    )
                    for name in archive.namelist():
                        if name.startswith("xl/worksheets/sheet") and name.endswith(
                            ".xml"
                        ):
                            sheet = archive.read(name)
                            assert b'<autoFilter ref="' in sheet
                            assert b'ySplit="1"' in sheet
                            assert b"<f>" not in sheet
            with ZipFile(BytesIO(payroll)) as archive:
                assert "Doi soat cham cong" in archive.read("xl/workbook.xml").decode(
                    "utf-8"
                )
                styles = archive.read("xl/styles.xml").decode("utf-8")
                assert "yyyy-mm-dd" in styles
                assert "VND" in styles
        async with sessions() as session:
            audits = (
                await session.scalars(
                    select(AuditLog).where(AuditLog.action == "hr.report.exported")
                )
            ).all()
            assert {audit.resource_id for audit in audits} == {"tasks", "payroll"}
            assert all(
                audit.after_json == {"report_kind": audit.resource_id, "row_count": 1}
                for audit in audits
            )
        await engine.dispose()

    asyncio.run(exercise())


def test_uncalculated_payroll_cannot_be_exported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_period(self: PayrollService, *_args: object):
        return SimpleNamespace(calculated_at=None)

    monkeypatch.setattr(PayrollService, "get_period", fake_period)

    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine)
        async with sessions() as session:
            service = HrReportService(session)
            with pytest.raises(DomainError) as error:
                await service.payroll(
                    _principal("SUPER_ADMIN"),
                    uuid4(),
                    audit=AuditService(session),
                    request_id="report-test",
                    user_agent="pytest",
                )
            assert error.value.code == "HR_PAYROLL_CALCULATION_REQUIRED"
            with pytest.raises(DomainError) as forbidden:
                await service.payroll(
                    _principal("MODERATOR", permissions=("hr.payroll.read",)),
                    uuid4(),
                    audit=AuditService(session),
                    request_id="report-test",
                    user_agent="pytest",
                )
            assert forbidden.value.code == "HR_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())
