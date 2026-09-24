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
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import (
    Attendance,
    AttendanceAssignment,
    AttendanceLocationEvidence,
    AttendanceLocationException,
    AttendanceStatus,
    AttendanceWorksite,
    AttendanceWorksitePolicy,
    AttendanceWorksiteStatus,
    Department,
    Employee,
    LeaveRequest,
    LeaveRequestStatus,
    OvertimeRequest,
    OvertimeRequestStatus,
)
from app.modules.hr.schemas import (
    CheckInRequest,
    CheckOutRequest,
    CreateDepartmentRequest,
    CreateEmployeeRequest,
    CreateLeaveRequest,
    CreateOvertimeRequest,
    LeaveDecisionRequest,
    OvertimeDecisionRequest,
    UpdateAttendanceRequest,
    UpdateDepartmentRequest,
    UpdateEmployeeRequest,
)
from app.modules.hr.service import HrService
from app.modules.notifications.models import Notification


async def _create_hr_tables(engine: object) -> None:
    async with engine.begin() as connection:  # type: ignore[union-attr]
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[
                    User.__table__,
                    Role.__table__,
                    UserRole.__table__,
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
                    AuditLog.__table__,
                    Notification.__table__,
                ],
            )
        )


def _principal(
    *, roles: tuple[str, ...] = (), permissions: tuple[str, ...] = ()
) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="operator@example.com",
        roles=roles,
        permissions=permissions,
    )


def _location_capture(*, note: str | None = None) -> dict[str, object]:
    capture: dict[str, object] = {
        "latitude": Decimal("10.776900"),
        "longitude": Decimal("106.700900"),
        "accuracy_meters": Decimal("18.50"),
        "client_captured_at": datetime(2026, 9, 21, 2, 30, tzinfo=UTC),
    }
    if note is not None:
        capture["note"] = note
    return capture


def test_department_creation_is_authorized_audited_and_searchable() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
        async with sessions() as session:
            created = await HrService(session).create_department(
                admin,
                CreateDepartmentRequest(
                    code="eng",
                    name="Khối Công nghệ",
                    description="Sản phẩm và nền tảng",
                ),
                audit=AuditService(session),
                request_id="hr-test",
                user_agent="pytest",
            )
            assert created.code == "ENG"
        async with sessions() as session:
            rows, total = await HrService(session).list_departments(
                admin, page=1, page_size=20, search="Công"
            )
            assert total == 1
            assert rows[0].name == "Khối Công nghệ"
        await engine.dispose()

    asyncio.run(exercise())


def test_department_access_rejects_user_role() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            with pytest.raises(DomainError) as denied:
                await HrService(session).list_departments(
                    _principal(roles=("USER",)), page=1, page_size=20, search=None
                )
            assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())


def test_department_name_can_be_updated_by_admin_and_is_audited() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="ENG", name="Engineering")
            session.add(department)
            await session.flush()
            department_id = department.id
        async with sessions() as session:
            updated = await HrService(session).update_department(
                admin,
                department_id,
                UpdateDepartmentRequest(
                    name="Phòng Kỹ thuật", description="Vận hành kỹ thuật"
                ),
                audit=AuditService(session),
                request_id="hr-test",
                user_agent="pytest",
            )
            assert updated.code == "ENG"
            assert updated.name == "Phòng Kỹ thuật"
            audit = await session.scalar(
                select(AuditLog).where(AuditLog.action == "hr.department.updated")
            )
            assert audit is not None
        async with sessions() as session:
            with pytest.raises(DomainError) as denied:
                await HrService(session).update_department(
                    _principal(roles=("USER",)),
                    department_id,
                    UpdateDepartmentRequest(name="Không được đổi"),
                    audit=AuditService(session),
                    request_id="hr-test",
                    user_agent="pytest",
                )
            assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())


def test_employee_creation_lists_salary_for_authorized_admin_only() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="ENG", name="Khối Công nghệ")
            session.add(department)
            await session.flush()
            department_id = department.id
        async with sessions() as session:
            created = await HrService(session).create_employee(
                admin,
                CreateEmployeeRequest(
                    employee_code="nv-001",
                    full_name="Nguyễn Minh An",
                    email="an@example.com",
                    department_id=department_id,
                    position="Kỹ sư phần mềm",
                    join_date=date(2026, 9, 1),
                    contract_type="FULL_TIME",
                    base_salary=Decimal("25000000"),
                ),
                audit=AuditService(session),
                request_id="employee-test",
                user_agent="pytest",
            )
            assert created.employee_code == "NV-001"
            assert created.base_salary == Decimal("25000000.00")
        async with sessions() as session:
            audit = await session.scalar(
                select(AuditLog).where(AuditLog.action == "hr.employee.created")
            )
            assert audit is not None
            assert audit.after_json is not None
            assert not {
                "full_name",
                "email",
                "phone",
                "base_salary",
                "user_id",
            }.intersection(audit.after_json)
        async with sessions() as session:
            rows, total = await HrService(session).list_employees(
                admin,
                page=1,
                page_size=20,
                search="Minh",
                department_id=department_id,
                employment_status=None,
            )
            assert total == 1
            assert rows[0].department_name == "Khối Công nghệ"
        await engine.dispose()

    asyncio.run(exercise())


def test_employee_link_requires_active_user_with_matching_email() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        linked_user = User(
            email="staff@example.com",
            status=UserStatus.ACTIVE,
            email_verified_at=datetime(2026, 9, 1, tzinfo=UTC),
        )
        async with sessions.begin() as session:
            session.add_all([User(id=admin.user_id, email=admin.email), linked_user])
            department = Department(code="OPS", name="Operations")
            session.add(department)
            await session.flush()
            department_id = department.id
            user_id = linked_user.id

        def payload(email: str) -> CreateEmployeeRequest:
            return CreateEmployeeRequest(
                employee_code="STAFF-1",
                user_id=user_id,
                full_name="Staff Member",
                email=email,
                department_id=department_id,
                position="Reviewer",
                join_date=date(2026, 9, 1),
            )

        async with sessions() as session:
            with pytest.raises(DomainError) as mismatch:
                await HrService(session).create_employee(
                    admin,
                    payload("other@example.com"),
                    audit=AuditService(session),
                    request_id="mismatch",
                    user_agent="pytest",
                )
            assert mismatch.value.code == "HR_USER_EMAIL_MISMATCH"
        async with sessions() as session:
            employee = await HrService(session).create_employee(
                admin,
                payload("staff@example.com"),
                audit=AuditService(session),
                request_id="linked",
                user_agent="pytest",
            )
            assert employee.user_id == user_id
        await engine.dispose()

    asyncio.run(exercise())


def test_employee_can_link_verified_user_after_provisional_profile() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email))
            user = User(
                email="staff@example.com",
                status=UserStatus.ACTIVE,
                email_verified_at=datetime(2026, 9, 1, tzinfo=UTC),
            )
            department = Department(code="OPS", name="Operations")
            session.add_all([user, department])
            await session.flush()
            user_id, department_id = user.id, department.id
        async with sessions() as session:
            employee = await HrService(session).create_employee(
                admin,
                CreateEmployeeRequest(
                    employee_code="STAFF-2",
                    full_name="Staff Member",
                    email="staff@example.com",
                    department_id=department_id,
                    position="Reviewer",
                    join_date=date(2026, 9, 1),
                    contract_type="PROBATION",
                ),
                audit=AuditService(session),
                request_id="provisional",
                user_agent="pytest",
            )
        async with sessions() as session:
            updated = await HrService(session).update_employee(
                admin,
                employee.id,
                UpdateEmployeeRequest(user_id=user_id, contract_type="FULL_TIME"),
                audit=AuditService(session),
                request_id="link",
                user_agent="pytest",
            )
            assert updated.user_id == user_id
            assert updated.contract_type == "FULL_TIME"
        async with sessions() as session:
            with pytest.raises(DomainError) as reassignment:
                await HrService(session).update_employee(
                    admin,
                    employee.id,
                    UpdateEmployeeRequest(user_id=uuid4()),
                    audit=AuditService(session),
                    request_id="reassign",
                    user_agent="pytest",
                )
            assert reassignment.value.code == "HR_USER_LINK_IMMUTABLE"
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize("role", ("VIEWER", "USER", "MODERATOR"))
def test_misassigned_hr_permissions_cannot_read_employee_or_department(
    role: str,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine)
        principal = _principal(
            roles=(role,),
            permissions=("hr.employees.read", "hr.departments.manage"),
        )
        async with sessions() as session:
            service = HrService(session)
            with pytest.raises(DomainError) as employee_error:
                await service.list_employees(
                    principal,
                    page=1,
                    page_size=20,
                    search=None,
                    department_id=None,
                    employment_status=None,
                )
            assert employee_error.value.code == "HR_FORBIDDEN"
            with pytest.raises(DomainError) as department_error:
                await service.list_departments(
                    principal, page=1, page_size=20, search=None
                )
            assert department_error.value.code == "HR_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())


def test_moderator_can_check_in_once_and_check_out_only_their_employee() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(roles=("MODERATOR",))
        async with sessions.begin() as session:
            session.add(
                User(
                    id=moderator.user_id,
                    email=moderator.email,
                    password_hash=None,
                )
            )
            department = Department(code="OPS", name="Vận hành")
            session.add(department)
            await session.flush()
            employee = Employee(
                employee_code="MOD-001",
                user_id=moderator.user_id,
                full_name="Moderator",
                email=moderator.email,
                department_id=department.id,
                position="Reviewer",
                join_date=date(2026, 9, 1),
            )
            worksite = AttendanceWorksite(
                code="SGN-HQ",
                name="Ho Chi Minh City HQ",
                status=AttendanceWorksiteStatus.ACTIVE,
            )
            session.add_all([employee, worksite])
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
                        max_accuracy_meters=25,
                    ),
                    AttendanceAssignment(
                        employee_id=employee.id,
                        worksite_id=worksite.id,
                        effective_from=date(2020, 1, 1),
                        schedule_code="MON_FRI_8H",
                        holiday_calendar_code="VN-HCM",
                    ),
                ]
            )

        async with sessions() as session:
            service = HrService(session)
            checked_in = await service.check_in(
                moderator,
                CheckInRequest(**_location_capture(note="Bắt đầu ca")),
                audit=AuditService(session),
                request_id="attendance-test",
                user_agent="pytest",
            )
            assert checked_in.check_out_at is None
            with pytest.raises(DomainError) as duplicate:
                await service.check_in(
                    moderator,
                    CheckInRequest(**_location_capture()),
                    audit=AuditService(session),
                    request_id="attendance-test",
                    user_agent="pytest",
                )
            assert duplicate.value.status_code == 409

        async with sessions() as session:
            checked_out = await HrService(session).check_out(
                moderator,
                CheckOutRequest(**_location_capture()),
                audit=AuditService(session),
                request_id="attendance-test",
                user_agent="pytest",
            )
            assert checked_out.check_out_at is not None

            attendance = await session.get(Attendance, checked_out.id)
            assert attendance is not None
            assert attendance.check_in_latitude is None
            assert attendance.check_out_longitude is None
            evidence = tuple(
                (
                    await session.scalars(
                        select(AttendanceLocationEvidence).where(
                            AttendanceLocationEvidence.attendance_id == attendance.id
                        )
                    )
                ).all()
            )
            assert len(evidence) == 2
            audit_rows = tuple(
                (
                    await session.scalars(
                        select(AuditLog).where(
                            AuditLog.action.in_(
                                [
                                    "hr.attendance.checked_in",
                                    "hr.attendance.checked_out",
                                ]
                            )
                        )
                    )
                ).all()
            )
            assert len(audit_rows) == 2
            assert all("10.776900" not in row.after_json for row in audit_rows)
        await engine.dispose()

    asyncio.run(exercise())


def test_location_capture_requires_required_evidence_and_rejects_client_geofence() -> (
    None
):
    valid = _location_capture()
    CheckInRequest(**valid)
    CheckOutRequest(**valid)

    with pytest.raises(ValueError):
        CheckInRequest(
            latitude=Decimal("10.776900"),
            longitude=Decimal("106.700900"),
            client_captured_at=datetime(2026, 9, 21, 2, 30, tzinfo=UTC),
        )

    with pytest.raises(ValueError):
        CheckOutRequest(**valid, inside_radius=True)


def test_moderator_attendance_history_contains_only_their_records() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(roles=("MODERATOR",))
        async with sessions.begin() as session:
            session.add(
                User(
                    id=moderator.user_id,
                    email=moderator.email,
                    password_hash=None,
                )
            )
            department = Department(code="OPS", name="Vận hành")
            session.add(department)
            await session.flush()
            own_employee = Employee(
                employee_code="MOD-001",
                user_id=moderator.user_id,
                full_name="Moderator",
                email=moderator.email,
                department_id=department.id,
                position="Reviewer",
                join_date=date(2026, 9, 1),
            )
            another_employee = Employee(
                employee_code="OPS-002",
                full_name="Other employee",
                email="other@example.com",
                department_id=department.id,
                position="Operator",
                join_date=date(2026, 9, 1),
            )
            session.add_all([own_employee, another_employee])
            await session.flush()
            own_employee_id = own_employee.id
            session.add_all(
                [
                    Attendance(
                        employee_id=own_employee.id,
                        work_date=date(2026, 9, 19),
                        check_in_at=datetime(2026, 9, 19, 1, tzinfo=UTC),
                    ),
                    Attendance(
                        employee_id=own_employee.id,
                        work_date=date(2026, 9, 20),
                        check_in_at=datetime(2026, 9, 20, 1, tzinfo=UTC),
                    ),
                    Attendance(
                        employee_id=another_employee.id,
                        work_date=date(2026, 9, 20),
                        check_in_at=datetime(2026, 9, 20, 1, tzinfo=UTC),
                    ),
                ]
            )

        async with sessions() as session:
            rows, total = await HrService(session).list_personal_attendance(
                moderator,
                page=1,
                page_size=20,
            )
            assert total == 2
            assert [row.work_date for row in rows] == [
                date(2026, 9, 20),
                date(2026, 9, 19),
            ]
            assert {row.employee_id for row in rows} == {own_employee_id}
        await engine.dispose()

    asyncio.run(exercise())


def test_attendance_self_service_rejects_viewer_role() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            with pytest.raises(DomainError) as denied:
                await HrService(session).list_personal_attendance(
                    _principal(roles=("VIEWER",)),
                    page=1,
                    page_size=20,
                )
            assert denied.value.code == "HR_ATTENDANCE_FORBIDDEN"
            assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())


def test_attendance_self_service_requires_linked_employee_profile() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            with pytest.raises(DomainError) as denied:
                await HrService(session).list_personal_attendance(
                    _principal(roles=("MODERATOR",)),
                    page=1,
                    page_size=20,
                )
            assert denied.value.code == "HR_EMPLOYEE_PROFILE_REQUIRED"
            assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())


def test_super_admin_can_filter_and_adjust_attendance_with_audit() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="OPS", name="Vận hành")
            session.add(department)
            await session.flush()
            employee = Employee(
                employee_code="OPS-001",
                full_name="Operations employee",
                email="operations@example.com",
                department_id=department.id,
                position="Operator",
                join_date=date(2026, 9, 1),
            )
            session.add(employee)
            await session.flush()
            attendance = Attendance(
                employee_id=employee.id,
                work_date=date(2026, 9, 20),
                check_in_at=datetime(2026, 9, 20, 1, tzinfo=UTC),
            )
            session.add_all(
                [
                    attendance,
                    Attendance(
                        employee_id=employee.id,
                        work_date=date(2026, 9, 19),
                        status=AttendanceStatus.ABSENT,
                    ),
                ]
            )
            await session.flush()
            attendance_id = attendance.id
            department_id = department.id

        async with sessions() as session:
            service = HrService(session)
            rows, total = await service.list_admin_attendance(
                admin,
                page=1,
                page_size=20,
                search="OPS-001",
                department_id=department_id,
                attendance_status=AttendanceStatus.PRESENT,
                work_date_from=date(2026, 9, 20),
                work_date_to=date(2026, 9, 20),
            )
            assert total == 1
            assert rows[0].employee_code == "OPS-001"
            assert rows[0].department_name == "Vận hành"

            updated = await service.update_attendance(
                admin,
                attendance_id,
                UpdateAttendanceRequest(
                    status=AttendanceStatus.LATE,
                    late_minutes=15,
                    note="Điều chỉnh theo xác nhận của quản lý",
                ),
                audit=AuditService(session),
                request_id="attendance-adjustment-test",
                user_agent="pytest",
            )
            assert updated.status == AttendanceStatus.LATE
            assert updated.late_minutes == 15
            audit = await session.scalar(
                select(AuditLog).where(AuditLog.action == "hr.attendance.adjusted")
            )
            assert audit is not None
            assert audit.before_json["status"] == "PRESENT"
            assert "note" not in audit.after_json
        await engine.dispose()

    asyncio.run(exercise())


def test_admin_attendance_filter_rejects_reverse_date_range() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            with pytest.raises(DomainError) as invalid:
                await HrService(session).list_admin_attendance(
                    _principal(roles=("SUPER_ADMIN",)),
                    page=1,
                    page_size=20,
                    search=None,
                    department_id=None,
                    attendance_status=None,
                    work_date_from=date(2026, 9, 21),
                    work_date_to=date(2026, 9, 20),
                )
            assert invalid.value.code == "HR_ATTENDANCE_DATE_RANGE_INVALID"
            assert invalid.value.status_code == 422
        await engine.dispose()

    asyncio.run(exercise())


def test_moderator_can_create_list_and_cancel_only_own_leave_request() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(roles=("MODERATOR",))
        other_user = _principal(roles=("MODERATOR",))
        async with sessions.begin() as session:
            session.add_all(
                [
                    User(
                        id=moderator.user_id,
                        email="moderator@example.com",
                        password_hash=None,
                    ),
                    User(
                        id=other_user.user_id,
                        email=other_user.email.replace("operator", "other"),
                        password_hash=None,
                    ),
                ]
            )
            department = Department(code="OPS", name="Vận hành")
            session.add(department)
            await session.flush()
            session.add_all(
                [
                    Employee(
                        employee_code="MOD-001",
                        user_id=moderator.user_id,
                        full_name="Moderator",
                        email=moderator.email,
                        department_id=department.id,
                        position="Reviewer",
                        join_date=date(2026, 9, 1),
                    ),
                    Employee(
                        employee_code="MOD-002",
                        user_id=other_user.user_id,
                        full_name="Other moderator",
                        email="other@example.com",
                        department_id=department.id,
                        position="Reviewer",
                        join_date=date(2026, 9, 1),
                    ),
                ]
            )
            await session.flush()
            other_employee = await session.scalar(
                select(Employee).where(Employee.user_id == other_user.user_id)
            )
            assert other_employee is not None
            other_request = LeaveRequest(
                employee_id=other_employee.id,
                leave_type="Annual leave",
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 1),
                reason="Personal appointment",
            )
            session.add(other_request)
            await session.flush()
            other_request_id = other_request.id

        async with sessions() as session:
            service = HrService(session)
            created = await service.create_leave_request(
                moderator,
                CreateLeaveRequest(
                    leave_type="Annual leave",
                    start_date=date(2026, 9, 24),
                    end_date=date(2026, 9, 25),
                    reason="Family commitment",
                ),
                audit=AuditService(session),
                request_id="leave-test",
                user_agent="pytest",
            )
            assert created.status == LeaveRequestStatus.PENDING
            assert created.employee_name == "Moderator"
            rows, total = await service.list_personal_leave_requests(
                moderator, page=1, page_size=20
            )
            assert total == 1
            assert rows[0].id == created.id
            with pytest.raises(DomainError) as not_owned:
                await service.cancel_leave_request(
                    moderator,
                    other_request_id,
                    audit=AuditService(session),
                    request_id="leave-test",
                    user_agent="pytest",
                )
            assert not_owned.value.code == "HR_LEAVE_REQUEST_NOT_FOUND"

            cancelled = await service.cancel_leave_request(
                moderator,
                created.id,
                audit=AuditService(session),
                request_id="leave-test",
                user_agent="pytest",
            )
            assert cancelled.status == LeaveRequestStatus.CANCELLED
        await engine.dispose()

    asyncio.run(exercise())


def test_linked_user_has_hr_self_service_without_moderator_role() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        employee_user = _principal(roles=("USER",))
        unlinked_user = _principal(roles=("USER",))
        async with sessions.begin() as session:
            session.add_all(
                [
                    User(
                        id=employee_user.user_id,
                        email=employee_user.email,
                        password_hash=None,
                    ),
                    User(
                        id=unlinked_user.user_id,
                        email="unlinked@example.com",
                        password_hash=None,
                    ),
                ]
            )
            department = Department(code="OPS", name="Operations")
            session.add(department)
            await session.flush()
            session.add(
                Employee(
                    employee_code="USER-HR-001",
                    user_id=employee_user.user_id,
                    full_name="Linked employee",
                    email=employee_user.email,
                    department_id=department.id,
                    position="Reviewer",
                    join_date=date(2026, 1, 1),
                )
            )

        async with sessions() as session:
            service = HrService(session)
            _, attendance_count = await service.list_personal_attendance(
                employee_user, page=1, page_size=20
            )
            assert attendance_count == 0
            leave = await service.create_leave_request(
                employee_user,
                CreateLeaveRequest(
                    leave_type="Annual leave",
                    start_date=date(2026, 10, 12),
                    end_date=date(2026, 10, 12),
                    reason="Personal leave",
                ),
                audit=AuditService(session),
                request_id="user-hr-self",
                user_agent="pytest",
            )
            overtime = await service.create_overtime_request(
                employee_user,
                CreateOvertimeRequest(
                    start_at=datetime(2026, 10, 13, 10, tzinfo=UTC),
                    end_at=datetime(2026, 10, 13, 11, tzinfo=UTC),
                    reason="Approved work request",
                ),
                audit=AuditService(session),
                request_id="user-hr-self",
                user_agent="pytest",
            )
            assert leave.status == LeaveRequestStatus.PENDING
            assert overtime.status == OvertimeRequestStatus.PENDING
            with pytest.raises(DomainError) as unlinked:
                await service.list_personal_attendance(
                    unlinked_user, page=1, page_size=20
                )
            assert unlinked.value.code == "HR_EMPLOYEE_PROFILE_REQUIRED"
            with pytest.raises(DomainError) as unlinked_leave:
                await service.list_personal_leave_requests(
                    unlinked_user, page=1, page_size=20
                )
            assert unlinked_leave.value.code == "HR_EMPLOYEE_PROFILE_REQUIRED"
            with pytest.raises(DomainError) as unlinked_overtime:
                await service.list_personal_overtime_requests(
                    unlinked_user, page=1, page_size=20
                )
            assert unlinked_overtime.value.code == "HR_EMPLOYEE_PROFILE_REQUIRED"
            viewer = AuthPrincipal(
                user_id=employee_user.user_id,
                session_id=uuid4(),
                email=employee_user.email,
                roles=("VIEWER",),
            )
            with pytest.raises(DomainError) as viewer_denied:
                await service.list_personal_leave_requests(viewer, page=1, page_size=20)
            assert viewer_denied.value.code == "HR_LEAVE_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())


def test_leave_request_rejects_overlap_with_pending_or_approved_leave() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(roles=("MODERATOR",))
        async with sessions.begin() as session:
            session.add(
                User(id=moderator.user_id, email=moderator.email, password_hash=None)
            )
            department = Department(code="OPS", name="Operations")
            session.add(department)
            await session.flush()
            session.add(
                Employee(
                    employee_code="LEAVE-001",
                    user_id=moderator.user_id,
                    full_name="Employee",
                    email=moderator.email,
                    department_id=department.id,
                    position="Reviewer",
                    join_date=date(2026, 1, 1),
                )
            )

        async with sessions() as session:
            service = HrService(session)

            async def request(start: date, end: date):
                return await service.create_leave_request(
                    moderator,
                    CreateLeaveRequest(
                        leave_type="Annual leave",
                        start_date=start,
                        end_date=end,
                        reason="Personal leave",
                    ),
                    audit=AuditService(session),
                    request_id="leave-overlap-test",
                    user_agent="pytest",
                )

            first = await request(date(2026, 10, 5), date(2026, 10, 6))
            with pytest.raises(DomainError) as overlapping:
                await request(date(2026, 10, 6), date(2026, 10, 7))
            assert overlapping.value.code == "HR_LEAVE_DATE_OVERLAP"
            await service.cancel_leave_request(
                moderator,
                first.id,
                audit=AuditService(session),
                request_id="leave-overlap-test",
                user_agent="pytest",
            )
            replacement = await request(date(2026, 10, 6), date(2026, 10, 7))
            assert replacement.status == LeaveRequestStatus.PENDING
            persisted = await session.get(LeaveRequest, replacement.id)
            assert persisted is not None
            persisted.status = LeaveRequestStatus.APPROVED
            await session.commit()
            with pytest.raises(DomainError) as approved_overlap:
                await request(date(2026, 10, 7), date(2026, 10, 7))
            assert approved_overlap.value.code == "HR_LEAVE_DATE_OVERLAP"
        await engine.dispose()

    asyncio.run(exercise())


def test_super_admin_decides_leave_with_audit_and_notification() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        moderator = _principal(roles=("MODERATOR",))
        async with sessions.begin() as session:
            session.add_all(
                [
                    User(id=admin.user_id, email=admin.email, password_hash=None),
                    User(
                        id=moderator.user_id,
                        email="moderator@example.com",
                        password_hash=None,
                    ),
                ]
            )
            department = Department(code="OPS", name="Vận hành")
            session.add(department)
            await session.flush()
            employee = Employee(
                employee_code="OPS-001",
                user_id=moderator.user_id,
                full_name="Moderator",
                email=moderator.email,
                department_id=department.id,
                position="Reviewer",
                join_date=date(2026, 9, 1),
            )
            session.add(employee)
            await session.flush()
            request = LeaveRequest(
                employee_id=employee.id,
                leave_type="Annual leave",
                start_date=date(2026, 9, 24),
                end_date=date(2026, 9, 25),
                reason="Sensitive personal detail",
            )
            session.add(request)
            await session.flush()
            request_id = request.id

        async with sessions() as session:
            service = HrService(session)
            approved = await service.decide_leave_request(
                admin,
                request_id,
                LeaveRequestStatus.APPROVED,
                LeaveDecisionRequest(decision_note="Approved by reviewer"),
                audit=AuditService(session),
                request_id="leave-decision-test",
                user_agent="pytest",
            )
            assert approved.status == LeaveRequestStatus.APPROVED
            assert approved.reviewed_by_user_id == admin.user_id
            audit = await session.scalar(
                select(AuditLog).where(AuditLog.action == "hr.leave.approved")
            )
            assert audit is not None
            assert "reason" not in audit.after_json
            assert "decision_note" not in audit.after_json
            notification = await session.scalar(
                select(Notification).where(Notification.user_id == moderator.user_id)
            )
            assert notification is not None
            assert notification.data_json["status"] == "APPROVED"
            with pytest.raises(DomainError) as invalid_transition:
                await service.decide_leave_request(
                    admin,
                    request_id,
                    LeaveRequestStatus.REJECTED,
                    LeaveDecisionRequest(),
                    audit=AuditService(session),
                    request_id="leave-decision-test",
                    user_agent="pytest",
                )
            assert invalid_transition.value.code == "HR_LEAVE_DECISION_INVALID"
        await engine.dispose()

    asyncio.run(exercise())


def test_moderator_can_create_list_and_cancel_own_overtime_request() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(roles=("MODERATOR",))
        async with sessions.begin() as session:
            session.add(
                User(id=moderator.user_id, email=moderator.email, password_hash=None)
            )
            department = Department(code="OPS", name="Vận hành")
            session.add(department)
            await session.flush()
            session.add(
                Employee(
                    employee_code="MOD-OT-001",
                    user_id=moderator.user_id,
                    full_name="Moderator",
                    email=moderator.email,
                    department_id=department.id,
                    position="Reviewer",
                    join_date=date(2026, 9, 1),
                )
            )

        async with sessions() as session:
            service = HrService(session)
            created = await service.create_overtime_request(
                moderator,
                CreateOvertimeRequest(
                    start_at=datetime(2026, 9, 24, 10, tzinfo=UTC),
                    end_at=datetime(2026, 9, 24, 13, tzinfo=UTC),
                    reason="Production incident support",
                ),
                audit=AuditService(session),
                request_id="overtime-test",
                user_agent="pytest",
            )
            assert created.status == OvertimeRequestStatus.PENDING
            rows, total = await service.list_personal_overtime_requests(
                moderator, page=1, page_size=20
            )
            assert total == 1
            assert rows[0].id == created.id
            with pytest.raises(DomainError) as overlap:
                await service.create_overtime_request(
                    moderator,
                    CreateOvertimeRequest(
                        start_at=datetime(2026, 9, 24, 12, tzinfo=UTC),
                        end_at=datetime(2026, 9, 24, 14, tzinfo=UTC),
                        reason="Overlapping support",
                    ),
                    audit=AuditService(session),
                    request_id="overtime-test",
                    user_agent="pytest",
                )
            assert overlap.value.code == "HR_OVERTIME_INTERVAL_OVERLAP"
            cancelled = await service.cancel_overtime_request(
                moderator,
                created.id,
                audit=AuditService(session),
                request_id="overtime-test",
                user_agent="pytest",
            )
            assert cancelled.status == OvertimeRequestStatus.CANCELLED
            replacement = await service.create_overtime_request(
                moderator,
                CreateOvertimeRequest(
                    start_at=datetime(2026, 9, 24, 12, tzinfo=UTC),
                    end_at=datetime(2026, 9, 24, 14, tzinfo=UTC),
                    reason="Replacement support",
                ),
                audit=AuditService(session),
                request_id="overtime-test",
                user_agent="pytest",
            )
            assert replacement.status == OvertimeRequestStatus.PENDING
            with pytest.raises(DomainError) as denied:
                await service.list_personal_overtime_requests(
                    _principal(roles=("VIEWER",)), page=1, page_size=20
                )
            assert denied.value.code == "HR_OVERTIME_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())


def test_super_admin_decides_overtime_with_audit_and_notification() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        moderator = _principal(roles=("MODERATOR",))
        async with sessions.begin() as session:
            session.add_all(
                [
                    User(id=admin.user_id, email=admin.email, password_hash=None),
                    User(
                        id=moderator.user_id,
                        email="overtime-moderator@example.com",
                        password_hash=None,
                    ),
                ]
            )
            department = Department(code="OPS", name="Vận hành")
            session.add(department)
            await session.flush()
            employee = Employee(
                employee_code="OPS-OT-001",
                user_id=moderator.user_id,
                full_name="Moderator",
                email="overtime-moderator@example.com",
                department_id=department.id,
                position="Reviewer",
                join_date=date(2026, 9, 1),
            )
            session.add(employee)
            await session.flush()
            request = OvertimeRequest(
                employee_id=employee.id,
                start_at=datetime(2026, 9, 24, 10, tzinfo=UTC),
                end_at=datetime(2026, 9, 24, 13, tzinfo=UTC),
                reason="Sensitive incident context",
            )
            session.add(request)
            await session.flush()
            request_id = request.id

        async with sessions() as session:
            service = HrService(session)
            approved = await service.decide_overtime_request(
                admin,
                request_id,
                OvertimeRequestStatus.APPROVED,
                OvertimeDecisionRequest(decision_note="Approved by reviewer"),
                audit=AuditService(session),
                request_id="overtime-decision-test",
                user_agent="pytest",
            )
            assert approved.status == OvertimeRequestStatus.APPROVED
            audit = await session.scalar(
                select(AuditLog).where(AuditLog.action == "hr.overtime.approved")
            )
            assert audit is not None
            assert "reason" not in audit.after_json
            assert "decision_note" not in audit.after_json
            notification = await session.scalar(
                select(Notification).where(Notification.user_id == moderator.user_id)
            )
            assert notification is not None
            assert notification.data_json["status"] == "APPROVED"
        await engine.dispose()

    asyncio.run(exercise())


def test_admin_overtime_filter_requires_timezone_aware_datetimes() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_hr_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            with pytest.raises(DomainError) as error:
                await HrService(session).list_admin_overtime_requests(
                    _principal(roles=("SUPER_ADMIN",)),
                    page=1,
                    page_size=20,
                    search=None,
                    department_id=None,
                    overtime_status=None,
                    start_at_from=datetime(2026, 9, 24, 10),
                    start_at_to=None,
                )
            assert error.value.code == "HR_OVERTIME_TIMEZONE_REQUIRED"
        await engine.dispose()

    asyncio.run(exercise())
