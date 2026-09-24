from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.auth.authorization import AuthorizationPolicy
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import (
    Attendance,
    AttendanceLocationException,
    AttendanceLocationExceptionStatus,
    AttendanceStatus,
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


@dataclass(frozen=True, slots=True)
class HrDashboardSummary:
    active_employee_count: int
    attendance_pending_count: int
    location_exception_pending_count: int
    leave_pending_count: int
    overtime_pending_count: int
    payroll_draft_count: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ModeratorHrDashboardSummary:
    profile_linked: bool
    work_date: date | None
    timezone: str | None
    attendance_status: AttendanceStatus | None
    check_in_at: datetime | None
    check_out_at: datetime | None
    leave_pending_count: int
    overtime_pending_count: int
    updated_at: datetime


class HrDashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _require_super_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_resource_scope(
            "SUPER_ADMIN" in principal.roles,
            lambda: DomainError(
                code="HR_DASHBOARD_FORBIDDEN",
                message="Only a super administrator can view the HR dashboard summary.",
                status_code=403,
            ),
        )

    @staticmethod
    def _require_moderator(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_resource_scope(
            "MODERATOR" in principal.roles,
            lambda: DomainError(
                code="HR_MODERATOR_DASHBOARD_FORBIDDEN",
                message="Only a moderator can view this personal HR dashboard.",
                status_code=403,
            ),
        )

    async def _count(self, model: type[Base], criterion: ColumnElement[bool]) -> int:
        return int(
            await self._session.scalar(
                select(func.count()).select_from(model).where(criterion)
            )
            or 0
        )

    async def summary(self, principal: AuthPrincipal) -> HrDashboardSummary:
        self._require_super_admin(principal)
        return HrDashboardSummary(
            active_employee_count=await self._count(
                Employee, Employee.employment_status == EmploymentStatus.ACTIVE
            ),
            attendance_pending_count=await self._count(
                Attendance, Attendance.status == AttendanceStatus.PENDING
            ),
            location_exception_pending_count=await self._count(
                AttendanceLocationException,
                AttendanceLocationException.status
                == AttendanceLocationExceptionStatus.PENDING,
            ),
            leave_pending_count=await self._count(
                LeaveRequest, LeaveRequest.status == LeaveRequestStatus.PENDING
            ),
            overtime_pending_count=await self._count(
                OvertimeRequest, OvertimeRequest.status == OvertimeRequestStatus.PENDING
            ),
            payroll_draft_count=await self._count(
                PayrollPeriod, PayrollPeriod.status == PayrollPeriodStatus.DRAFT
            ),
            updated_at=datetime.now(UTC),
        )

    async def moderator_summary(
        self, principal: AuthPrincipal
    ) -> ModeratorHrDashboardSummary:
        self._require_moderator(principal)
        employee = await self._session.scalar(
            select(Employee).where(Employee.user_id == principal.user_id)
        )
        now = datetime.now(UTC)
        if employee is None:
            return ModeratorHrDashboardSummary(
                profile_linked=False,
                work_date=None,
                timezone=None,
                attendance_status=None,
                check_in_at=None,
                check_out_at=None,
                leave_pending_count=0,
                overtime_pending_count=0,
                updated_at=now,
            )

        hr_service = HrService(self._session)
        workday = await hr_service.get_personal_attendance_workday_context(principal)
        attendance = None
        if workday.work_date is not None:
            attendance = await self._session.scalar(
                select(Attendance).where(
                    Attendance.employee_id == employee.id,
                    Attendance.work_date == workday.work_date,
                )
            )
        return ModeratorHrDashboardSummary(
            profile_linked=True,
            work_date=workday.work_date,
            timezone=workday.timezone,
            attendance_status=attendance.status if attendance is not None else None,
            check_in_at=attendance.check_in_at if attendance is not None else None,
            check_out_at=attendance.check_out_at if attendance is not None else None,
            leave_pending_count=await self._count(
                LeaveRequest,
                (LeaveRequest.employee_id == employee.id)
                & (LeaveRequest.status == LeaveRequestStatus.PENDING),
            ),
            overtime_pending_count=await self._count(
                OvertimeRequest,
                (OvertimeRequest.employee_id == employee.id)
                & (OvertimeRequest.status == OvertimeRequestStatus.PENDING),
            ),
            updated_at=now,
        )
