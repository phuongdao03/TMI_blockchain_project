"""Super Administrator XLSX exports with explicit, bounded data projections."""

from calendar import monthrange
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import (
    Attendance,
    AttendanceStatus,
    Department,
    Employee,
    EmploymentStatus,
    LeaveRequestStatus,
    OvertimeRequestStatus,
)
from app.modules.hr.payroll_service import PayrollService
from app.modules.hr.service import HrService
from app.modules.hr.xlsx_export import (
    MAX_EXPORT_ROWS,
    ExportColumn,
    ExportSheet,
    build_xlsx,
)
from app.modules.tasks.models import TaskPriority, TaskStatus
from app.modules.tasks.service import TaskService


class HrReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

    @staticmethod
    def _require_admin(principal: AuthPrincipal, permission: str) -> None:
        def forbidden() -> DomainError:
            return DomainError(
                code="HR_FORBIDDEN",
                message="You do not have permission to export HR data.",
                status_code=403,
            )

        AuthorizationPolicy.require_resource_scope(
            "SUPER_ADMIN" in principal.roles, forbidden
        )
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission=permission, compatible_roles=frozenset({"SUPER_ADMIN"})
            ),
            forbidden,
        )

    async def _audit_export(
        self,
        principal: AuthPrincipal,
        *,
        kind: str,
        row_count: int,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> None:
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.report.exported",
            resource_type="hr_report",
            resource_id=kind,
            after={"report_kind": kind, "row_count": row_count},
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()

    @staticmethod
    def _check_limit(row_count: int) -> None:
        if row_count > MAX_EXPORT_ROWS:
            raise DomainError(
                code="HR_EXPORT_TOO_LARGE",
                message="The report exceeds 10,000 rows. Narrow the filters.",
                status_code=422,
            )

    async def tasks(
        self,
        principal: AuthPrincipal,
        *,
        search: str | None,
        task_status: TaskStatus | None,
        priority: TaskPriority | None,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> bytes:
        self._require_admin(principal, "work.tasks.read")
        rows, total = await TaskService(self._session).list_tasks(
            principal,
            page=1,
            page_size=MAX_EXPORT_ROWS + 1,
            search=search,
            task_status=task_status,
            priority=priority,
        )
        self._check_limit(total)
        content = build_xlsx(
            (
                ExportSheet(
                    "Cong viec",
                    (
                        ExportColumn("title", "Tên công việc", width=42),
                        ExportColumn("status", "Trạng thái"),
                        ExportColumn("priority", "Mức ưu tiên"),
                        ExportColumn("assignee", "Mã người phụ trách", width=40),
                        ExportColumn("due_at", "Hạn hoàn thành", "datetime"),
                        ExportColumn("completed_at", "Hoàn thành lúc", "datetime"),
                    ),
                    tuple(
                        {
                            "title": row.title,
                            "status": row.status.value,
                            "priority": row.priority.value,
                            "assignee": (
                                str(row.assignee_employee_id)
                                if row.assignee_employee_id
                                else ""
                            ),
                            "due_at": row.due_at,
                            "completed_at": row.completed_at,
                        }
                        for row in rows
                    ),
                ),
            )
        )
        await self._audit_export(
            principal,
            kind="tasks",
            row_count=len(rows),
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
        )
        return content

    async def payroll(
        self,
        principal: AuthPrincipal,
        payroll_period_id: UUID,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> bytes:
        self._require_admin(principal, "hr.payroll.read")
        period = await PayrollService(self._session).get_period(
            principal, payroll_period_id
        )
        if period.calculated_at is None:
            raise DomainError(
                code="HR_PAYROLL_CALCULATION_REQUIRED",
                message="Calculate the payroll period before exporting it.",
                status_code=409,
            )
        self._check_limit(len(period.entries))
        period_end = date(
            period.period_month.year,
            period.period_month.month,
            monthrange(period.period_month.year, period.period_month.month)[1],
        )
        employee_ids = [entry.employee_id for entry in period.entries]
        attendance_rows: tuple[Row[tuple[Attendance, str, str]], ...] = ()
        if employee_ids:
            attendance_rows = tuple(
                (
                    await self._session.execute(
                        select(Attendance, Employee.employee_code, Employee.full_name)
                        .join(Employee, Employee.id == Attendance.employee_id)
                        .where(
                            Attendance.employee_id.in_(employee_ids),
                            Attendance.work_date >= period.period_month,
                            Attendance.work_date <= period_end,
                        )
                        .order_by(Employee.employee_code, Attendance.work_date)
                        .limit(MAX_EXPORT_ROWS + 1)
                    )
                ).all()
            )
        self._check_limit(len(attendance_rows))
        content = build_xlsx(
            (
                ExportSheet(
                    "Ky luong",
                    (
                        ExportColumn("month", "Kỳ lương", "date"),
                        ExportColumn("status", "Trạng thái"),
                        ExportColumn("currency", "Tiền tệ"),
                        ExportColumn("worksite", "Mã điểm làm việc", width=40),
                        ExportColumn("standard_workdays", "Ngày công chuẩn", "integer"),
                    ),
                    (
                        {
                            "month": period.period_month,
                            "status": period.status.value,
                            "currency": period.currency,
                            "worksite": str(period.worksite_id),
                            "standard_workdays": period.standard_workdays,
                        },
                    ),
                ),
                ExportSheet(
                    "Chi tiet luong",
                    (
                        ExportColumn("employee_code", "Mã nhân viên"),
                        ExportColumn("employee_name", "Họ và tên", width=32),
                        ExportColumn("status", "Trạng thái kỳ"),
                        ExportColumn("attendance_workdays", "Ngày công", "decimal"),
                        ExportColumn(
                            "approved_overtime_hours", "Giờ OT duyệt", "decimal"
                        ),
                        ExportColumn("base_salary", "Lương cơ bản", "vnd"),
                        ExportColumn("allowance", "Phụ cấp", "vnd"),
                        ExportColumn("social_insurance", "BHXH", "vnd"),
                        ExportColumn("income_tax", "Thuế thu nhập", "vnd"),
                        ExportColumn("daily_salary", "Lương ngày", "vnd"),
                        ExportColumn("overtime_salary", "Lương OT", "vnd"),
                        ExportColumn("gross_pay", "Tổng trước khấu trừ", "vnd"),
                        ExportColumn("total_deductions", "Khấu trừ", "vnd"),
                        ExportColumn("net_pay", "Thực lĩnh", "vnd"),
                    ),
                    tuple(
                        {
                            "employee_code": entry.employee_code,
                            "employee_name": entry.employee_name,
                            "status": period.status.value,
                            "attendance_workdays": entry.attendance_workdays,
                            "approved_overtime_hours": entry.approved_overtime_hours,
                            "base_salary": entry.base_salary,
                            "allowance": entry.allowance,
                            "social_insurance": entry.social_insurance,
                            "income_tax": entry.income_tax,
                            "daily_salary": entry.daily_salary,
                            "overtime_salary": entry.overtime_salary,
                            "gross_pay": entry.gross_pay,
                            "total_deductions": entry.total_deductions,
                            "net_pay": entry.net_pay,
                        }
                        for entry in period.entries
                    ),
                ),
                ExportSheet(
                    "Doi soat cham cong",
                    (
                        ExportColumn("employee_code", "Mã nhân viên"),
                        ExportColumn("employee_name", "Họ và tên", width=32),
                        ExportColumn("work_date", "Ngày công", "date"),
                        ExportColumn("status", "Trạng thái"),
                        ExportColumn("check_in_at", "Giờ vào UTC", "datetime"),
                        ExportColumn("check_out_at", "Giờ ra UTC", "datetime"),
                        ExportColumn("late_minutes", "Phút đi muộn", "integer"),
                        ExportColumn("early_leave_minutes", "Phút về sớm", "integer"),
                    ),
                    tuple(
                        {
                            "employee_code": code,
                            "employee_name": name,
                            "work_date": attendance.work_date,
                            "status": attendance.status.value,
                            "check_in_at": self._utc(attendance.check_in_at),
                            "check_out_at": self._utc(attendance.check_out_at),
                            "late_minutes": attendance.late_minutes,
                            "early_leave_minutes": attendance.early_leave_minutes,
                        }
                        for attendance, code, name in attendance_rows
                    ),
                ),
            )
        )
        await self._audit_export(
            principal,
            kind="payroll",
            row_count=len(period.entries),
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
        )
        return content

    async def departments(
        self,
        principal: AuthPrincipal,
        *,
        search: str | None,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> bytes:
        self._require_admin(principal, "hr.departments.manage")
        statement = select(Department)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(Department.code.ilike(pattern), Department.name.ilike(pattern))
            )
        departments = (
            await self._session.scalars(
                statement.order_by(Department.name, Department.id).limit(
                    MAX_EXPORT_ROWS + 1
                )
            )
        ).all()
        self._check_limit(len(departments))
        content = build_xlsx(
            (
                ExportSheet(
                    "Phong ban",
                    (
                        ExportColumn("code", "Mã phòng ban"),
                        ExportColumn("name", "Tên phòng ban", width=32),
                        ExportColumn("status", "Trạng thái"),
                    ),
                    tuple(
                        {
                            "code": department.code,
                            "name": department.name,
                            "status": department.status.value,
                        }
                        for department in departments
                    ),
                ),
            )
        )
        await self._audit_export(
            principal,
            kind="departments",
            row_count=len(departments),
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
        )
        return content

    async def employees(
        self,
        principal: AuthPrincipal,
        *,
        search: str | None,
        department_id: UUID | None,
        employment_status: EmploymentStatus | None,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> bytes:
        self._require_admin(principal, "hr.employees.read")
        statement = select(Employee, Department.name).join(
            Department, Department.id == Employee.department_id
        )
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Employee.employee_code.ilike(pattern),
                    Employee.full_name.ilike(pattern),
                    Employee.email.ilike(pattern),
                )
            )
        if department_id:
            statement = statement.where(Employee.department_id == department_id)
        if employment_status:
            statement = statement.where(Employee.employment_status == employment_status)
        employees = (
            (
                await self._session.execute(
                    statement.order_by(Employee.full_name, Employee.id).limit(
                        MAX_EXPORT_ROWS + 1
                    )
                )
            )
            .tuples()
            .all()
        )
        self._check_limit(len(employees))
        content = build_xlsx(
            (
                ExportSheet(
                    "Nhan vien",
                    (
                        ExportColumn("employee_code", "Mã nhân viên"),
                        ExportColumn("full_name", "Họ và tên", width=32),
                        ExportColumn("department_name", "Phòng ban", width=32),
                        ExportColumn("position", "Chức danh", width=28),
                        ExportColumn("employment_status", "Trạng thái"),
                        ExportColumn("join_date", "Ngày vào", "date"),
                    ),
                    tuple(
                        {
                            "employee_code": employee.employee_code,
                            "full_name": employee.full_name,
                            "department_name": department_name,
                            "position": employee.position,
                            "employment_status": employee.employment_status.value,
                            "join_date": employee.join_date,
                        }
                        for employee, department_name in employees
                    ),
                ),
            )
        )
        await self._audit_export(
            principal,
            kind="employees",
            row_count=len(employees),
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
        )
        return content

    async def attendance(
        self,
        principal: AuthPrincipal,
        *,
        search: str | None,
        department_id: UUID | None,
        attendance_status: AttendanceStatus | None,
        work_date_from: date | None,
        work_date_to: date | None,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> bytes:
        rows, total = await HrService(self._session).list_admin_attendance(
            principal,
            page=1,
            page_size=MAX_EXPORT_ROWS + 1,
            search=search,
            department_id=department_id,
            attendance_status=attendance_status,
            work_date_from=work_date_from,
            work_date_to=work_date_to,
        )
        self._check_limit(total)
        content = build_xlsx(
            (
                ExportSheet(
                    "Cham cong",
                    (
                        ExportColumn("employee_code", "Mã nhân viên"),
                        ExportColumn("employee_name", "Họ và tên", width=32),
                        ExportColumn("department_name", "Phòng ban", width=30),
                        ExportColumn("work_date", "Ngày công", "date"),
                        ExportColumn("status", "Trạng thái"),
                        ExportColumn("check_in_at", "Giờ vào UTC", "datetime"),
                        ExportColumn("check_out_at", "Giờ ra UTC", "datetime"),
                        ExportColumn("late_minutes", "Phút đi muộn", "integer"),
                        ExportColumn("early_leave_minutes", "Phút về sớm", "integer"),
                    ),
                    tuple(
                        {
                            "employee_code": row.employee_code,
                            "employee_name": row.employee_name,
                            "department_name": row.department_name,
                            "work_date": row.work_date,
                            "status": row.status.value,
                            "check_in_at": self._utc(row.check_in_at),
                            "check_out_at": self._utc(row.check_out_at),
                            "late_minutes": row.late_minutes,
                            "early_leave_minutes": row.early_leave_minutes,
                        }
                        for row in rows
                    ),
                ),
            )
        )
        await self._audit_export(
            principal,
            kind="attendance",
            row_count=len(rows),
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
        )
        return content

    async def leave(
        self,
        principal: AuthPrincipal,
        *,
        search: str | None,
        department_id: UUID | None,
        leave_status: LeaveRequestStatus | None,
        start_date_from: date | None,
        start_date_to: date | None,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> bytes:
        rows, total = await HrService(self._session).list_admin_leave_requests(
            principal,
            page=1,
            page_size=MAX_EXPORT_ROWS + 1,
            search=search,
            department_id=department_id,
            leave_status=leave_status,
            start_date_from=start_date_from,
            start_date_to=start_date_to,
        )
        self._check_limit(total)
        content = build_xlsx(
            (
                ExportSheet(
                    "Nghi phep",
                    (
                        ExportColumn("employee_code", "Mã nhân viên"),
                        ExportColumn("employee_name", "Họ và tên", width=32),
                        ExportColumn("department_name", "Phòng ban", width=30),
                        ExportColumn("leave_type", "Loại phép"),
                        ExportColumn("start_date", "Từ ngày", "date"),
                        ExportColumn("end_date", "Đến ngày", "date"),
                        ExportColumn("status", "Trạng thái"),
                        ExportColumn("reviewed_at", "Duyệt lúc UTC", "datetime"),
                    ),
                    tuple(
                        {
                            "employee_code": row.employee_code,
                            "employee_name": row.employee_name,
                            "department_name": row.department_name,
                            "leave_type": row.leave_type,
                            "start_date": row.start_date,
                            "end_date": row.end_date,
                            "status": row.status.value,
                            "reviewed_at": self._utc(row.reviewed_at),
                        }
                        for row in rows
                    ),
                ),
            )
        )
        await self._audit_export(
            principal,
            kind="leave",
            row_count=len(rows),
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
        )
        return content

    async def overtime(
        self,
        principal: AuthPrincipal,
        *,
        search: str | None,
        department_id: UUID | None,
        overtime_status: OvertimeRequestStatus | None,
        start_at_from: datetime | None,
        start_at_to: datetime | None,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> bytes:
        rows, total = await HrService(self._session).list_admin_overtime_requests(
            principal,
            page=1,
            page_size=MAX_EXPORT_ROWS + 1,
            search=search,
            department_id=department_id,
            overtime_status=overtime_status,
            start_at_from=start_at_from,
            start_at_to=start_at_to,
        )
        self._check_limit(total)
        content = build_xlsx(
            (
                ExportSheet(
                    "Tang ca",
                    (
                        ExportColumn("employee_code", "Mã nhân viên"),
                        ExportColumn("employee_name", "Họ và tên", width=32),
                        ExportColumn("department_name", "Phòng ban", width=30),
                        ExportColumn("start_at", "Bắt đầu UTC", "datetime"),
                        ExportColumn("end_at", "Kết thúc UTC", "datetime"),
                        ExportColumn("status", "Trạng thái"),
                        ExportColumn("reviewed_at", "Duyệt lúc UTC", "datetime"),
                    ),
                    tuple(
                        {
                            "employee_code": row.employee_code,
                            "employee_name": row.employee_name,
                            "department_name": row.department_name,
                            "start_at": self._utc(row.start_at),
                            "end_at": self._utc(row.end_at),
                            "status": row.status.value,
                            "reviewed_at": self._utc(row.reviewed_at),
                        }
                        for row in rows
                    ),
                ),
            )
        )
        await self._audit_export(
            principal,
            kind="overtime",
            row_count=len(rows),
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
        )
        return content
