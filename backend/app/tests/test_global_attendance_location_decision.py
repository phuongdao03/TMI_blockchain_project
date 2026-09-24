import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import Role, User, UserRole
from app.modules.auth.session_service import AuthPrincipal
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
    AttendanceWorksiteStatus,
    Department,
    Employee,
)
from app.modules.hr.schemas import (
    AttendanceLocationExceptionDecisionRequest,
    CheckInRequest,
    CreateAttendanceWorksitePolicyRequest,
)
from app.modules.hr.service import HrService
from app.modules.notifications.models import Notification

NOW = datetime(2026, 9, 21, 1, 30, tzinfo=UTC)


async def _create_tables(engine: object) -> None:
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
                    Notification.__table__,
                    AuditLog.__table__,
                ],
            )
        )


def _principal(*, role: str, email: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email=email,
        roles=(role,),
        permissions=(),
    )


def _capture(*, latitude: str, accuracy_meters: str = "12.50") -> CheckInRequest:
    return CheckInRequest(
        latitude=Decimal(latitude),
        longitude=Decimal("106.700900"),
        accuracy_meters=Decimal(accuracy_meters),
        client_captured_at=NOW,
        note="Field attendance",
    )


async def _seed_global_attendance(
    session: AsyncSession,
    moderator: AuthPrincipal,
    admin: AuthPrincipal,
    *,
    radius_meters: int = 100,
    max_accuracy_meters: int = 25,
    policy_effective_to: date | None = None,
) -> tuple[UUID, UUID]:
    session.add_all(
        [
            User(id=moderator.user_id, email=moderator.email, password_hash=None),
            User(id=admin.user_id, email=admin.email, password_hash=None),
        ]
    )
    super_admin_role = Role(code="SUPER_ADMIN")
    session.add(super_admin_role)
    await session.flush()
    session.add(UserRole(user_id=admin.user_id, role_id=super_admin_role.id))
    department = Department(code="OPS", name="Operations")
    session.add(department)
    await session.flush()
    employee = Employee(
        employee_code="OPS-001",
        user_id=moderator.user_id,
        full_name="Avery Patel",
        email=moderator.email,
        department_id=department.id,
        position="Field reviewer",
        join_date=date(2026, 9, 1),
    )
    worksite = AttendanceWorksite(
        code="SGN-HQ",
        name="Ho Chi Minh City HQ",
        status=AttendanceWorksiteStatus.ACTIVE,
    )
    session.add_all([employee, worksite])
    await session.flush()
    policy = AttendanceWorksitePolicy(
        worksite_id=worksite.id,
        effective_from=date(2026, 9, 1),
        effective_to=policy_effective_to,
        timezone="Asia/Ho_Chi_Minh",
        latitude=Decimal("10.776900"),
        longitude=Decimal("106.700900"),
        radius_meters=radius_meters,
        max_accuracy_meters=max_accuracy_meters,
    )
    assignment = AttendanceAssignment(
        employee_id=employee.id,
        worksite_id=worksite.id,
        effective_from=date(2026, 9, 1),
        schedule_code="MON_FRI_8H",
        holiday_calendar_code="VN-HCM",
    )
    session.add_all([policy, assignment])
    await session.flush()
    return employee.id, worksite.id


def test_accepted_location_evidence_creates_present_attendance() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(role="MODERATOR", email="moderator@example.com")
        admin = _principal(role="SUPER_ADMIN", email="admin@example.com")
        async with sessions.begin() as session:
            await _seed_global_attendance(session, moderator, admin)

        original_now = HrService.__dict__["_now"]
        HrService._now = staticmethod(lambda: NOW)
        try:
            async with sessions() as session:
                attendance = await HrService(session).check_in(
                    moderator,
                    _capture(latitude="10.776900"),
                    audit=AuditService(session),
                    request_id="location-decision",
                    user_agent="pytest",
                )
                evidence = await session.scalar(
                    select(AttendanceLocationEvidence).where(
                        AttendanceLocationEvidence.attendance_id == attendance.id
                    )
                )
                exception = await session.scalar(
                    select(AttendanceLocationException).where(
                        AttendanceLocationException.attendance_id == attendance.id
                    )
                )

                assert attendance.status == AttendanceStatus.PRESENT
                assert attendance.work_date == date(2026, 9, 21)
                assert evidence is not None
                assert evidence.event_type == AttendanceLocationEventType.CHECK_IN
                assert evidence.outcome == AttendanceLocationOutcome.ACCEPTED
                assert exception is None
                workday_context = await HrService(
                    session
                ).get_personal_attendance_workday_context(moderator)
                assert workday_context.work_date == date(2026, 9, 21)
                assert workday_context.timezone == "Asia/Ho_Chi_Minh"
                personal_evidence = await HrService(
                    session
                ).list_personal_attendance_location_evidence(moderator, attendance.id)
                assert personal_evidence[0].worksite_name == "Ho Chi Minh City HQ"
                assert personal_evidence[0].latitude == Decimal("10.776900")
                admin_evidence = await HrService(
                    session
                ).list_admin_attendance_location_evidence(admin, attendance.id)
                assert admin_evidence[0].longitude == Decimal("106.700900")
                with pytest.raises(DomainError) as unauthorized:
                    await HrService(session).list_admin_attendance_location_evidence(
                        moderator, attendance.id
                    )
                assert unauthorized.value.code == "HR_FORBIDDEN"
        finally:
            HrService._now = original_now
            await engine.dispose()

    asyncio.run(exercise())


def test_employee_cannot_read_another_employees_location_evidence() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(role="MODERATOR", email="moderator@example.com")
        admin = _principal(role="SUPER_ADMIN", email="admin@example.com")
        async with sessions.begin() as session:
            _, worksite_id = await _seed_global_attendance(session, moderator, admin)
            department = await session.scalar(
                select(Department).where(Department.code == "OPS")
            )
            policy = await session.scalar(
                select(AttendanceWorksitePolicy).where(
                    AttendanceWorksitePolicy.worksite_id == worksite_id
                )
            )
            assert department is not None
            assert policy is not None
            other_employee = Employee(
                employee_code="OPS-002",
                full_name="Other employee",
                email="other@example.com",
                department_id=department.id,
                position="Reviewer",
                join_date=date(2026, 9, 1),
            )
            session.add(other_employee)
            await session.flush()
            other_attendance = Attendance(
                employee_id=other_employee.id,
                work_date=date(2026, 9, 21),
                check_in_at=NOW,
                check_in_latitude=Decimal("10.776900"),
                check_in_longitude=Decimal("106.700900"),
            )
            session.add(other_attendance)
            await session.flush()
            session.add(
                AttendanceLocationEvidence(
                    attendance_id=other_attendance.id,
                    event_type=AttendanceLocationEventType.CHECK_IN,
                    worksite_policy_id=policy.id,
                    client_captured_at=NOW,
                    latitude=Decimal("10.776900"),
                    longitude=Decimal("106.700900"),
                    accuracy_meters=Decimal("12.50"),
                    distance_meters=Decimal("0"),
                    effective_timezone="Asia/Ho_Chi_Minh",
                    permitted_radius_meters=100,
                    max_accuracy_meters=25,
                    outcome=AttendanceLocationOutcome.ACCEPTED,
                    retention_until=datetime(2028, 9, 21, 1, 30, tzinfo=UTC),
                )
            )
            other_attendance_id = other_attendance.id

        async with sessions() as session:
            rows = await HrService(session).list_personal_attendance_location_evidence(
                moderator, other_attendance_id
            )
            assert rows == ()

        await engine.dispose()

    asyncio.run(exercise())


def test_outside_worksite_stays_pending_until_super_admin_approves() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(role="MODERATOR", email="moderator@example.com")
        admin = _principal(role="SUPER_ADMIN", email="admin@example.com")
        async with sessions.begin() as session:
            await _seed_global_attendance(session, moderator, admin, radius_meters=100)

        original_now = HrService.__dict__["_now"]
        HrService._now = staticmethod(lambda: NOW)
        try:
            async with sessions() as session:
                pending = await HrService(session).check_in(
                    moderator,
                    _capture(latitude="10.786900"),
                    audit=AuditService(session),
                    request_id="location-decision",
                    user_agent="pytest",
                )
                exception = await session.scalar(
                    select(AttendanceLocationException).where(
                        AttendanceLocationException.attendance_id == pending.id
                    )
                )
                evidence = await session.scalar(
                    select(AttendanceLocationEvidence).where(
                        AttendanceLocationEvidence.attendance_id == pending.id
                    )
                )

                assert pending.status == AttendanceStatus.PENDING
                assert exception is not None
                assert exception.status == AttendanceLocationExceptionStatus.PENDING
                assert evidence is not None
                assert evidence.outcome == AttendanceLocationOutcome.OUTSIDE_WORKSITE
                notifications = tuple(
                    await session.scalars(
                        select(Notification).where(
                            Notification.user_id == admin.user_id
                        )
                    )
                )
                assert len(notifications) == 1
                notification = notifications[0]
                assert notification.type == "HR_ATTENDANCE_LOCATION_REVIEW_REQUIRED"
                assert notification.data_json == {
                    "actionPath": "/admin/attendance",
                    "attendanceId": str(pending.id),
                }
                assert "latitude" not in notification.body.lower()
                assert "longitude" not in notification.body.lower()

                exceptions, total = await HrService(
                    session
                ).list_attendance_location_exceptions(
                    admin,
                    page=1,
                    page_size=20,
                    exception_status=AttendanceLocationExceptionStatus.PENDING,
                )
                assert total == 1
                assert exceptions[0].employee_name == "Avery Patel"
                assert exceptions[0].evidence.latitude == Decimal("10.786900")

                resolved = await HrService(
                    session
                ).decide_attendance_location_exception(
                    admin,
                    exception.id,
                    AttendanceLocationExceptionDecisionRequest(
                        status=AttendanceLocationExceptionStatus.APPROVED,
                        decision_note="Verified field assignment.",
                    ),
                    audit=AuditService(session),
                    request_id="location-decision",
                    user_agent="pytest",
                )
                refreshed_attendance = await session.get(Attendance, pending.id)
                refreshed_evidence = await session.get(
                    AttendanceLocationEvidence, evidence.id
                )

                assert resolved.status == AttendanceLocationExceptionStatus.APPROVED
                assert refreshed_attendance is not None
                assert refreshed_attendance.status == AttendanceStatus.PRESENT
                assert refreshed_evidence is not None
                assert (
                    refreshed_evidence.outcome
                    == AttendanceLocationOutcome.OUTSIDE_WORKSITE
                )
                audit_rows = tuple(
                    (
                        await session.scalars(
                            select(AuditLog).where(
                                AuditLog.action.in_(
                                    [
                                        "hr.attendance.checked_in",
                                        "hr.attendance_location_exception.decided",
                                    ]
                                )
                            )
                        )
                    ).all()
                )
                assert len(audit_rows) == 2
                assert all("10.786900" not in row.after_json for row in audit_rows)
        finally:
            HrService._now = original_now
            await engine.dispose()

    asyncio.run(exercise())


def test_low_accuracy_creates_a_pending_exception_before_distance_outcome() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(role="MODERATOR", email="moderator@example.com")
        admin = _principal(role="SUPER_ADMIN", email="admin@example.com")
        async with sessions.begin() as session:
            await _seed_global_attendance(session, moderator, admin)

        original_now = HrService.__dict__["_now"]
        HrService._now = staticmethod(lambda: NOW)
        try:
            async with sessions() as session:
                attendance = await HrService(session).check_in(
                    moderator,
                    _capture(latitude="10.786900", accuracy_meters="50.00"),
                    audit=AuditService(session),
                    request_id="location-decision",
                    user_agent="pytest",
                )
                evidence = await session.scalar(
                    select(AttendanceLocationEvidence).where(
                        AttendanceLocationEvidence.attendance_id == attendance.id
                    )
                )

                assert attendance.status == AttendanceStatus.PENDING
                assert evidence is not None
                assert evidence.outcome == AttendanceLocationOutcome.LOW_ACCURACY
        finally:
            HrService._now = original_now
            await engine.dispose()

    asyncio.run(exercise())


def test_assignment_locks_a_worksite_timezone_for_later_policies() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(role="MODERATOR", email="moderator@example.com")
        admin = _principal(role="SUPER_ADMIN", email="admin@example.com")
        async with sessions.begin() as session:
            _, worksite_id = await _seed_global_attendance(
                session,
                moderator,
                admin,
                policy_effective_to=date(2026, 9, 21),
            )

        async with sessions() as session:
            with pytest.raises(DomainError) as locked:
                await HrService(session).create_attendance_worksite_policy(
                    admin,
                    worksite_id,
                    CreateAttendanceWorksitePolicyRequest(
                        effective_from=date(2026, 9, 22),
                        timezone="America/New_York",
                        latitude=Decimal("40.712800"),
                        longitude=Decimal("-74.006000"),
                        radius_meters=100,
                        max_accuracy_meters=25,
                    ),
                    audit=AuditService(session),
                    request_id="timezone-lock",
                    user_agent="pytest",
                )
            assert locked.value.code == "HR_ATTENDANCE_WORKSITE_TIMEZONE_LOCKED"
        await engine.dispose()

    asyncio.run(exercise())


def test_exact_location_is_redacted_and_purged_after_24_months() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(role="MODERATOR", email="moderator@example.com")
        admin = _principal(role="SUPER_ADMIN", email="admin@example.com")
        async with sessions.begin() as session:
            await _seed_global_attendance(session, moderator, admin)

        original_now = HrService.__dict__["_now"]
        try:
            HrService._now = staticmethod(lambda: NOW)
            async with sessions() as session:
                attendance = await HrService(session).check_in(
                    moderator,
                    _capture(latitude="10.776900"),
                    audit=AuditService(session),
                    request_id="location-retention",
                    user_agent="pytest",
                )
                evidence = await session.scalar(
                    select(AttendanceLocationEvidence).where(
                        AttendanceLocationEvidence.attendance_id == attendance.id
                    )
                )
                assert evidence is not None
                assert evidence.retention_until.replace(tzinfo=UTC) == datetime(
                    2028, 9, 21, 1, 30, tzinfo=UTC
                )
                attendance_id = attendance.id
                evidence_id = evidence.id
                await session.commit()

            HrService._now = staticmethod(
                lambda: datetime(2028, 9, 21, 1, 30, tzinfo=UTC)
            )
            async with sessions() as session:
                redacted = await HrService(
                    session
                ).list_personal_attendance_location_evidence(moderator, attendance_id)
                assert redacted[0].latitude is None
                assert redacted[0].longitude is None

            async with sessions() as session:
                purged = await HrService(session).purge_expired_attendance_locations()
                refreshed_evidence = await session.get(
                    AttendanceLocationEvidence, evidence_id
                )
                refreshed_attendance = await session.get(Attendance, attendance_id)
                assert purged == 1
                assert refreshed_evidence is not None
                assert refreshed_evidence.latitude is None
                assert refreshed_evidence.longitude is None
                assert refreshed_evidence.location_purged_at is not None
                assert refreshed_evidence.location_purged_at.replace(
                    tzinfo=UTC
                ) == datetime(2028, 9, 21, 1, 30, tzinfo=UTC)
                assert refreshed_attendance is not None
                assert refreshed_attendance.check_in_latitude is None
                assert refreshed_attendance.check_in_longitude is None
        finally:
            HrService._now = original_now
            await engine.dispose()

    asyncio.run(exercise())


def test_workday_context_is_empty_when_employee_has_no_active_location_policy() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        moderator = _principal(role="MODERATOR", email="moderator@example.com")
        async with sessions.begin() as session:
            session.add(
                User(
                    id=moderator.user_id,
                    email=moderator.email,
                    password_hash=None,
                )
            )
            department = Department(code="OPS", name="Operations")
            session.add(department)
            await session.flush()
            session.add(
                Employee(
                    employee_code="OPS-002",
                    user_id=moderator.user_id,
                    full_name="Morgan Lee",
                    email=moderator.email,
                    department_id=department.id,
                    position="Reviewer",
                    join_date=date(2026, 9, 1),
                )
            )

        async with sessions() as session:
            context = await HrService(session).get_personal_attendance_workday_context(
                moderator
            )
            assert context.work_date is None
            assert context.timezone is None
            with pytest.raises(DomainError) as denied:
                await HrService(session).get_personal_attendance_workday_context(
                    _principal(role="VIEWER", email="viewer@example.com")
                )
            assert denied.value.code == "HR_ATTENDANCE_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())
