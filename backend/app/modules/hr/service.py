from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.location import (
    calculate_geodesic_distance_meters,
    is_accuracy_acceptable,
    is_within_radius,
    local_work_date_for,
)
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
    EmploymentStatus,
    LeaveRequest,
    LeaveRequestStatus,
    OvertimeRequest,
    OvertimeRequestStatus,
)
from app.modules.hr.schemas import (
    AdminAttendanceData,
    AdminAttendanceLocationExceptionData,
    AdminLeaveRequestData,
    AdminOvertimeRequestData,
    AttendanceAssignmentData,
    AttendanceData,
    AttendanceLocationEvidenceReviewData,
    AttendanceLocationExceptionData,
    AttendanceLocationExceptionDecisionRequest,
    AttendanceWorkdayContextData,
    AttendanceWorksiteData,
    AttendanceWorksitePolicyData,
    CheckInRequest,
    CheckOutRequest,
    CreateAttendanceAssignmentRequest,
    CreateAttendanceWorksitePolicyRequest,
    CreateAttendanceWorksiteRequest,
    CreateDepartmentRequest,
    CreateEmployeeRequest,
    CreateLeaveRequest,
    CreateOvertimeRequest,
    DepartmentData,
    EmployeeData,
    LeaveDecisionRequest,
    LeaveRequestData,
    OvertimeDecisionRequest,
    OvertimeRequestData,
    UpdateAttendanceRequest,
    UpdateAttendanceWorksiteRequest,
    UpdateDepartmentRequest,
    UpdateEmployeeRequest,
)
from app.modules.notifications.models import Notification

ATTENDANCE_LOCATION_RETENTION_MONTHS = 24


class HrService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _add_calendar_months(value: datetime, months: int) -> datetime:
        month_index = value.month - 1 + months
        target_year = value.year + month_index // 12
        target_month = month_index % 12 + 1
        return value.replace(
            year=target_year,
            month=target_month,
            day=min(value.day, monthrange(target_year, target_month)[1]),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

    @classmethod
    def _location_evidence_has_expired(
        cls, evidence: AttendanceLocationEvidence
    ) -> bool:
        return cls._as_utc(evidence.retention_until) <= cls._as_utc(cls._now())

    @staticmethod
    def _require(principal: AuthPrincipal, permission: str) -> None:
        AuthorizationPolicy.require_resource_scope(
            "SUPER_ADMIN" in principal.roles,
            lambda: DomainError(
                code="HR_FORBIDDEN",
                message="You do not have permission to access HR data.",
                status_code=403,
            ),
        )
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission=permission,
                compatible_roles=frozenset({"SUPER_ADMIN"}),
            ),
            lambda: DomainError(
                code="HR_FORBIDDEN",
                message="You do not have permission to access HR data.",
                status_code=403,
            ),
        )

    @staticmethod
    def _require_attendance_configuration_admin(principal: AuthPrincipal) -> None:
        """Keep precise worksite locations confined to Super Admins.

        The permission catalog still drives navigation and discoverability, but
        a future permission grant must not expose exact administrative GPS
        coordinates to another role.
        """
        AuthorizationPolicy.require_resource_scope(
            "SUPER_ADMIN" in principal.roles,
            lambda: DomainError(
                code="HR_FORBIDDEN",
                message="Only a super administrator can manage attendance worksites.",
                status_code=403,
            ),
        )

    async def list_departments(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        search: str | None,
    ) -> tuple[tuple[DepartmentData, ...], int]:
        self._require(principal, "hr.departments.manage")
        criteria: tuple[ColumnElement[bool], ...] = ()
        if search:
            pattern = f"%{search.strip()}%"
            criteria = (
                or_(Department.code.ilike(pattern), Department.name.ilike(pattern)),
            )
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(Department).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(Department)
                    .where(*criteria)
                    .order_by(Department.name)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(DepartmentData.model_validate(row) for row in rows), total

    async def create_department(
        self,
        principal: AuthPrincipal,
        payload: CreateDepartmentRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> DepartmentData:
        self._require(principal, "hr.departments.manage")
        code = payload.code.upper()
        duplicate = await self._session.scalar(
            select(Department.id).where(
                or_(Department.code == code, Department.name == payload.name)
            )
        )
        if duplicate is not None:
            raise DomainError(
                code="HR_DEPARTMENT_EXISTS",
                message="A department with this code or name already exists.",
                status_code=409,
            )
        department = Department(
            code=code,
            name=payload.name,
            description=payload.description,
        )
        self._session.add(department)
        await self._session.flush()
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.department.created",
            resource_type="department",
            resource_id=str(department.id),
            after={"code": department.code, "name": department.name},
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return DepartmentData.model_validate(department)

    async def update_department(
        self,
        principal: AuthPrincipal,
        department_id: UUID,
        payload: UpdateDepartmentRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> DepartmentData:
        self._require(principal, "hr.departments.manage")
        department = await self._session.get(Department, department_id)
        if department is None:
            raise DomainError(
                code="HR_DEPARTMENT_NOT_FOUND",
                message="Department not found.",
                status_code=404,
            )
        duplicate = await self._session.scalar(
            select(Department.id).where(
                Department.name == payload.name, Department.id != department_id
            )
        )
        if duplicate is not None:
            raise DomainError(
                code="HR_DEPARTMENT_EXISTS",
                message="A department with this name already exists.",
                status_code=409,
            )
        before: dict[str, object] = {
            "name": department.name,
            "description": department.description,
        }
        department.name = payload.name
        department.description = payload.description
        await self._session.flush()
        await self._session.refresh(department)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.department.updated",
            resource_type="department",
            resource_id=str(department.id),
            before=before,
            after={"name": department.name, "description": department.description},
            request_id=request_id,
            user_agent=user_agent,
        )
        result = DepartmentData.model_validate(department)
        await self._session.commit()
        return result

    @staticmethod
    def _employee_data(employee: Employee, department_name: str) -> EmployeeData:
        return EmployeeData.model_validate(
            {
                **{
                    field: getattr(employee, field)
                    for field in EmployeeData.model_fields
                    if field != "department_name"
                },
                "department_name": department_name,
            }
        )

    async def list_employees(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        search: str | None,
        department_id: UUID | None,
        employment_status: EmploymentStatus | None,
    ) -> tuple[tuple[EmployeeData, ...], int]:
        self._require(principal, "hr.employees.read")
        criteria = []
        if search:
            pattern = f"%{search.strip()}%"
            criteria.append(
                or_(
                    Employee.employee_code.ilike(pattern),
                    Employee.full_name.ilike(pattern),
                    Employee.email.ilike(pattern),
                )
            )
        if department_id:
            criteria.append(Employee.department_id == department_id)
        if employment_status:
            criteria.append(Employee.employment_status == employment_status)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(Employee).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.execute(
                    select(Employee, Department.name)
                    .join(Department, Department.id == Employee.department_id)
                    .where(*criteria)
                    .order_by(Employee.full_name)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).tuples()
        )
        return tuple(self._employee_data(row[0], row[1]) for row in rows), total

    async def create_employee(
        self,
        principal: AuthPrincipal,
        payload: CreateEmployeeRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> EmployeeData:
        self._require(principal, "hr.employees.manage")
        department = await self._session.get(Department, payload.department_id)
        if department is None:
            raise DomainError(
                code="HR_DEPARTMENT_NOT_FOUND",
                message="Department not found.",
                status_code=404,
            )
        code = payload.employee_code.upper()
        if payload.user_id is not None:
            linked_user = await self._session.get(User, payload.user_id)
            if (
                linked_user is None
                or linked_user.status != UserStatus.ACTIVE
                or linked_user.email_verified_at is None
            ):
                raise DomainError(
                    code="HR_USER_NOT_ACTIVE",
                    message="Linked user must be active and verified.",
                    status_code=422,
                )
            if linked_user.email.casefold() != str(payload.email).casefold():
                raise DomainError(
                    code="HR_USER_EMAIL_MISMATCH",
                    message="Employee email must match linked user.",
                    status_code=422,
                )
        duplicate_criteria = [Employee.employee_code == code]
        if payload.user_id:
            duplicate_criteria.append(Employee.user_id == payload.user_id)
        duplicate = await self._session.scalar(
            select(Employee.id).where(or_(*duplicate_criteria))
        )
        if duplicate is not None:
            raise DomainError(
                code="HR_EMPLOYEE_EXISTS",
                message="Employee code or linked user already exists.",
                status_code=409,
            )
        employee = Employee(
            **payload.model_dump(exclude={"employee_code"}, by_alias=False),
            employee_code=code,
        )
        self._session.add(employee)
        await self._session.flush()
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.employee.created",
            resource_type="employee",
            resource_id=str(employee.id),
            after={
                "employee_code": employee.employee_code,
                "department_id": str(employee.department_id),
                "employment_status": employee.employment_status.value,
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return self._employee_data(employee, department.name)

    async def get_employee(
        self, principal: AuthPrincipal, employee_id: UUID
    ) -> EmployeeData:
        self._require(principal, "hr.employees.read")
        row = (
            await self._session.execute(
                select(Employee, Department.name)
                .join(Department, Department.id == Employee.department_id)
                .where(Employee.id == employee_id)
            )
        ).one_or_none()
        if row is None:
            raise DomainError(
                code="HR_EMPLOYEE_NOT_FOUND",
                message="Employee not found.",
                status_code=404,
            )
        return self._employee_data(row[0], row[1])

    async def update_employee(
        self,
        principal: AuthPrincipal,
        employee_id: UUID,
        payload: UpdateEmployeeRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> EmployeeData:
        self._require(principal, "hr.employees.manage")
        employee = await self._session.get(Employee, employee_id)
        if employee is None:
            raise DomainError(
                code="HR_EMPLOYEE_NOT_FOUND",
                message="Employee not found.",
                status_code=404,
            )
        changes = payload.model_dump(exclude_unset=True, by_alias=False)
        if "user_id" in changes:
            target_id = changes["user_id"]
            if employee.user_id is not None and target_id != employee.user_id:
                raise DomainError(
                    code="HR_USER_LINK_IMMUTABLE",
                    message="Linked user cannot be reassigned.",
                    status_code=409,
                )
            if target_id is not None:
                linked_user = await self._session.get(User, target_id)
                if (
                    linked_user is None
                    or linked_user.status != UserStatus.ACTIVE
                    or linked_user.email_verified_at is None
                ):
                    raise DomainError(
                        code="HR_USER_NOT_ACTIVE",
                        message="Linked user must be active and verified.",
                        status_code=422,
                    )
                target_email = str(changes.get("email", employee.email))
                if linked_user.email.casefold() != target_email.casefold():
                    raise DomainError(
                        code="HR_USER_EMAIL_MISMATCH",
                        message="Employee email must match linked user.",
                        status_code=422,
                    )
                linked_elsewhere = await self._session.scalar(
                    select(Employee.id).where(
                        Employee.user_id == target_id, Employee.id != employee_id
                    )
                )
                if linked_elsewhere is not None:
                    raise DomainError(
                        code="HR_EMPLOYEE_EXISTS",
                        message="Linked user already has an employee record.",
                        status_code=409,
                    )
        if "email" in changes and employee.user_id is not None:
            linked_user = await self._session.get(User, employee.user_id)
            if (
                linked_user is None
                or linked_user.email.casefold() != str(changes["email"]).casefold()
            ):
                raise DomainError(
                    code="HR_USER_EMAIL_MISMATCH",
                    message="Employee email must match linked user.",
                    status_code=422,
                )
        if "department_id" in changes:
            department = await self._session.get(Department, changes["department_id"])
            if department is None:
                raise DomainError(
                    code="HR_DEPARTMENT_NOT_FOUND",
                    message="Department not found.",
                    status_code=404,
                )
        before: dict[str, object] = {
            "department_id": str(employee.department_id),
            "employment_status": employee.employment_status.value,
            "position": employee.position,
        }
        for field, value in changes.items():
            setattr(employee, field, value)
        await self._session.flush()
        department_name = await self._session.scalar(
            select(Department.name).where(Department.id == employee.department_id)
        )
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.employee.updated",
            resource_type="employee",
            resource_id=str(employee.id),
            before=before,
            after={
                "department_id": str(employee.department_id),
                "employment_status": employee.employment_status.value,
                "position": employee.position,
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.refresh(employee)
        result = self._employee_data(employee, str(department_name))
        await self._session.commit()
        return result

    @staticmethod
    def _attendance_data(attendance: Attendance, employee_name: str) -> AttendanceData:
        return AttendanceData.model_validate(
            {
                **{
                    field: getattr(attendance, field)
                    for field in AttendanceData.model_fields
                    if field != "employee_name"
                },
                "employee_name": employee_name,
            }
        )

    @staticmethod
    def _admin_attendance_data(
        attendance: Attendance,
        *,
        employee_code: str,
        employee_name: str,
        department_name: str,
    ) -> AdminAttendanceData:
        return AdminAttendanceData.model_validate(
            {
                **{
                    field: getattr(attendance, field)
                    for field in AttendanceData.model_fields
                    if field != "employee_name"
                },
                "employee_name": employee_name,
                "employee_code": employee_code,
                "department_name": department_name,
            }
        )

    @staticmethod
    def _attendance_audit_snapshot(attendance: Attendance) -> dict[str, object]:
        return {
            "work_date": attendance.work_date.isoformat(),
            "status": attendance.status.value,
            "check_in_at": (
                attendance.check_in_at.isoformat() if attendance.check_in_at else None
            ),
            "check_out_at": (
                attendance.check_out_at.isoformat() if attendance.check_out_at else None
            ),
            "late_minutes": attendance.late_minutes,
            "early_leave_minutes": attendance.early_leave_minutes,
        }

    async def list_admin_attendance(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        search: str | None,
        department_id: UUID | None,
        attendance_status: AttendanceStatus | None,
        work_date_from: date | None,
        work_date_to: date | None,
    ) -> tuple[tuple[AdminAttendanceData, ...], int]:
        self._require(principal, "hr.attendance.read")
        if (
            work_date_from is not None
            and work_date_to is not None
            and work_date_from > work_date_to
        ):
            raise DomainError(
                code="HR_ATTENDANCE_DATE_RANGE_INVALID",
                message="Work date start must not be after work date end.",
                status_code=422,
            )
        criteria = []
        if search:
            pattern = f"%{search.strip()}%"
            criteria.append(
                or_(
                    Employee.employee_code.ilike(pattern),
                    Employee.full_name.ilike(pattern),
                    Employee.email.ilike(pattern),
                )
            )
        if department_id:
            criteria.append(Employee.department_id == department_id)
        if attendance_status:
            criteria.append(Attendance.status == attendance_status)
        if work_date_from:
            criteria.append(Attendance.work_date >= work_date_from)
        if work_date_to:
            criteria.append(Attendance.work_date <= work_date_to)
        total = int(
            await self._session.scalar(
                select(func.count())
                .select_from(Attendance)
                .join(Employee, Employee.id == Attendance.employee_id)
                .where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.execute(
                    select(
                        Attendance,
                        Employee.employee_code,
                        Employee.full_name,
                        Department.name,
                    )
                    .join(Employee, Employee.id == Attendance.employee_id)
                    .join(Department, Department.id == Employee.department_id)
                    .where(*criteria)
                    .order_by(Attendance.work_date.desc(), Employee.full_name)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).tuples()
        )
        return (
            tuple(
                self._admin_attendance_data(
                    row[0],
                    employee_code=row[1],
                    employee_name=row[2],
                    department_name=row[3],
                )
                for row in rows
            ),
            total,
        )

    async def get_admin_attendance(
        self, principal: AuthPrincipal, attendance_id: UUID
    ) -> AdminAttendanceData:
        self._require(principal, "hr.attendance.read")
        row = (
            await self._session.execute(
                select(
                    Attendance,
                    Employee.employee_code,
                    Employee.full_name,
                    Department.name,
                )
                .join(Employee, Employee.id == Attendance.employee_id)
                .join(Department, Department.id == Employee.department_id)
                .where(Attendance.id == attendance_id)
            )
        ).one_or_none()
        if row is None:
            raise DomainError(
                code="HR_ATTENDANCE_NOT_FOUND",
                message="Attendance record not found.",
                status_code=404,
            )
        return self._admin_attendance_data(
            row[0],
            employee_code=row[1],
            employee_name=row[2],
            department_name=row[3],
        )

    async def update_attendance(
        self,
        principal: AuthPrincipal,
        attendance_id: UUID,
        payload: UpdateAttendanceRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AdminAttendanceData:
        self._require(principal, "hr.attendance.adjust")
        attendance = await self._session.get(Attendance, attendance_id)
        if attendance is None:
            raise DomainError(
                code="HR_ATTENDANCE_NOT_FOUND",
                message="Attendance record not found.",
                status_code=404,
            )
        changes = payload.model_dump(exclude_unset=True, by_alias=False)
        if not changes:
            raise DomainError(
                code="HR_ATTENDANCE_UPDATE_REQUIRED",
                message="Provide at least one attendance field to update.",
                status_code=422,
            )
        if "status" in changes and changes["status"] != attendance.status:
            unresolved_exception = await self._session.scalar(
                select(AttendanceLocationException.id).where(
                    AttendanceLocationException.attendance_id == attendance.id,
                    AttendanceLocationException.status.in_(
                        (
                            AttendanceLocationExceptionStatus.PENDING,
                            AttendanceLocationExceptionStatus.REJECTED,
                        )
                    ),
                )
            )
            if unresolved_exception is not None:
                raise DomainError(
                    code="HR_ATTENDANCE_LOCATION_EXCEPTION_DECISION_REQUIRED",
                    message=(
                        "Attendance with a location exception must be decided "
                        "through the location-exception workflow."
                    ),
                    status_code=409,
                )
        check_in_at = changes.get("check_in_at", attendance.check_in_at)
        check_out_at = changes.get("check_out_at", attendance.check_out_at)
        if check_out_at is not None and check_in_at is None:
            raise DomainError(
                code="HR_ATTENDANCE_TIME_INVALID",
                message="Check-in time is required before check-out time.",
                status_code=422,
            )
        if check_in_at is not None and check_out_at is not None:
            if check_out_at <= check_in_at:
                raise DomainError(
                    code="HR_ATTENDANCE_TIME_INVALID",
                    message="Check-out time must be after check-in time.",
                    status_code=422,
                )
        before = self._attendance_audit_snapshot(attendance)
        for field, value in changes.items():
            setattr(attendance, field, value)
        await self._session.flush()
        await self._session.refresh(attendance)
        employee = await self._session.get(Employee, attendance.employee_id)
        if employee is None:
            raise DomainError(
                code="HR_EMPLOYEE_NOT_FOUND",
                message="Employee not found.",
                status_code=404,
            )
        department_name = await self._session.scalar(
            select(Department.name).where(Department.id == employee.department_id)
        )
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.attendance.adjusted",
            resource_type="attendance",
            resource_id=str(attendance.id),
            before=before,
            after=self._attendance_audit_snapshot(attendance),
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._admin_attendance_data(
            attendance,
            employee_code=employee.employee_code,
            employee_name=employee.full_name,
            department_name=str(department_name),
        )
        await self._session.commit()
        return data

    @staticmethod
    def _attendance_worksite_data(
        worksite: AttendanceWorksite,
    ) -> AttendanceWorksiteData:
        return AttendanceWorksiteData.model_validate(worksite)

    @staticmethod
    def _attendance_worksite_audit_snapshot(
        worksite: AttendanceWorksite,
    ) -> dict[str, object]:
        return {
            "code": worksite.code,
            "name": worksite.name,
            "status": worksite.status.value,
        }

    @staticmethod
    def _attendance_policy_data(
        policy: AttendanceWorksitePolicy,
    ) -> AttendanceWorksitePolicyData:
        return AttendanceWorksitePolicyData.model_validate(policy)

    @staticmethod
    def _attendance_policy_audit_snapshot(
        policy: AttendanceWorksitePolicy,
    ) -> dict[str, object]:
        return {
            "worksite_id": str(policy.worksite_id),
            "effective_from": policy.effective_from.isoformat(),
            "effective_to": (
                policy.effective_to.isoformat() if policy.effective_to else None
            ),
            "timezone": policy.timezone,
            "radius_meters": policy.radius_meters,
            "max_accuracy_meters": policy.max_accuracy_meters,
        }

    @staticmethod
    def _attendance_assignment_data(
        assignment: AttendanceAssignment,
        *,
        employee_code: str,
        employee_name: str,
        worksite_code: str,
        worksite_name: str,
    ) -> AttendanceAssignmentData:
        return AttendanceAssignmentData.model_validate(
            {
                **{
                    field: getattr(assignment, field)
                    for field in AttendanceAssignmentData.model_fields
                    if field
                    not in {
                        "employee_code",
                        "employee_name",
                        "worksite_code",
                        "worksite_name",
                    }
                },
                "employee_code": employee_code,
                "employee_name": employee_name,
                "worksite_code": worksite_code,
                "worksite_name": worksite_name,
            }
        )

    @staticmethod
    def _attendance_assignment_audit_snapshot(
        assignment: AttendanceAssignment,
    ) -> dict[str, object]:
        return {
            "employee_id": str(assignment.employee_id),
            "worksite_id": str(assignment.worksite_id),
            "effective_from": assignment.effective_from.isoformat(),
            "effective_to": (
                assignment.effective_to.isoformat() if assignment.effective_to else None
            ),
            "schedule_code": assignment.schedule_code,
            "holiday_calendar_code": assignment.holiday_calendar_code,
        }

    @staticmethod
    def _effective_range_overlap(
        model: type[AttendanceWorksitePolicy] | type[AttendanceAssignment],
        *,
        effective_from: date,
        effective_to: date | None,
    ) -> tuple[ColumnElement[bool], ...]:
        criteria: list[ColumnElement[bool]] = [
            or_(model.effective_to.is_(None), model.effective_to >= effective_from)
        ]
        if effective_to is not None:
            criteria.append(model.effective_from <= effective_to)
        return tuple(criteria)

    @staticmethod
    def _is_effective_on(
        *, effective_from: date, effective_to: date | None, work_date: date
    ) -> bool:
        return effective_from <= work_date and (
            effective_to is None or work_date <= effective_to
        )

    async def _resolve_attendance_location_policy(
        self, *, employee_id: UUID, occurred_at: datetime
    ) -> tuple[AttendanceWorksitePolicy, date]:
        """Resolve one active policy using the worksite's IANA-local workday.

        The broad UTC window keeps the SQL prefilter safe for all supported
        global timezones.  The precise effective-date decision happens only
        after converting with the candidate policy's immutable IANA timezone.
        """
        server_date = occurred_at.date()
        earliest_possible_work_date = server_date - timedelta(days=1)
        latest_possible_work_date = server_date + timedelta(days=1)
        rows = (
            await self._session.execute(
                select(AttendanceAssignment, AttendanceWorksitePolicy)
                .join(
                    AttendanceWorksitePolicy,
                    AttendanceWorksitePolicy.worksite_id
                    == AttendanceAssignment.worksite_id,
                )
                .join(
                    AttendanceWorksite,
                    AttendanceWorksite.id == AttendanceAssignment.worksite_id,
                )
                .where(
                    AttendanceAssignment.employee_id == employee_id,
                    AttendanceWorksite.status == AttendanceWorksiteStatus.ACTIVE,
                    AttendanceAssignment.effective_from <= latest_possible_work_date,
                    or_(
                        AttendanceAssignment.effective_to.is_(None),
                        AttendanceAssignment.effective_to
                        >= earliest_possible_work_date,
                    ),
                    AttendanceWorksitePolicy.effective_from
                    <= latest_possible_work_date,
                    or_(
                        AttendanceWorksitePolicy.effective_to.is_(None),
                        AttendanceWorksitePolicy.effective_to
                        >= earliest_possible_work_date,
                    ),
                )
            )
        ).tuples()
        matches: list[tuple[AttendanceWorksitePolicy, date]] = []
        for assignment, policy in rows:
            work_date = local_work_date_for(
                occurred_at=occurred_at, timezone=policy.timezone
            )
            if self._is_effective_on(
                effective_from=assignment.effective_from,
                effective_to=assignment.effective_to,
                work_date=work_date,
            ) and self._is_effective_on(
                effective_from=policy.effective_from,
                effective_to=policy.effective_to,
                work_date=work_date,
            ):
                matches.append((policy, work_date))
        if not matches:
            raise DomainError(
                code="HR_ATTENDANCE_LOCATION_POLICY_REQUIRED",
                message="No active attendance location policy applies to this workday.",
                status_code=422,
            )
        if len(matches) != 1:
            raise DomainError(
                code="HR_ATTENDANCE_LOCATION_POLICY_AMBIGUOUS",
                message=(
                    "More than one attendance location policy applies to this workday."
                ),
                status_code=409,
            )
        return matches[0]

    @staticmethod
    def _location_outcome(
        *, payload: CheckInRequest | CheckOutRequest, policy: AttendanceWorksitePolicy
    ) -> tuple[AttendanceLocationOutcome, Decimal]:
        distance_meters = calculate_geodesic_distance_meters(
            latitude_a=payload.latitude,
            longitude_a=payload.longitude,
            latitude_b=policy.latitude,
            longitude_b=policy.longitude,
        )
        # Weak GPS cannot establish that an employee is outside a worksite, so
        # accuracy is evaluated before the radius and stays immutable in evidence.
        if not is_accuracy_acceptable(
            accuracy_meters=payload.accuracy_meters,
            max_accuracy_meters=policy.max_accuracy_meters,
        ):
            return AttendanceLocationOutcome.LOW_ACCURACY, distance_meters
        if not is_within_radius(
            distance_meters=distance_meters,
            radius_meters=policy.radius_meters,
        ):
            return AttendanceLocationOutcome.OUTSIDE_WORKSITE, distance_meters
        return AttendanceLocationOutcome.ACCEPTED, distance_meters

    async def _record_attendance_location_evidence(
        self,
        *,
        attendance: Attendance,
        event_type: AttendanceLocationEventType,
        policy: AttendanceWorksitePolicy,
        payload: CheckInRequest | CheckOutRequest,
        distance_meters: Decimal,
        outcome: AttendanceLocationOutcome,
        received_at: datetime,
    ) -> AttendanceLocationEvidence:
        evidence = AttendanceLocationEvidence(
            attendance_id=attendance.id,
            event_type=event_type,
            worksite_policy_id=policy.id,
            client_captured_at=payload.client_captured_at,
            received_at=received_at,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_meters=payload.accuracy_meters,
            distance_meters=distance_meters,
            effective_timezone=policy.timezone,
            permitted_radius_meters=policy.radius_meters,
            max_accuracy_meters=policy.max_accuracy_meters,
            outcome=outcome,
            retention_until=self._add_calendar_months(
                received_at, ATTENDANCE_LOCATION_RETENTION_MONTHS
            ),
        )
        self._session.add(evidence)
        await self._session.flush()
        return evidence

    async def _create_pending_location_exception(
        self,
        *,
        attendance: Attendance,
        evidence: AttendanceLocationEvidence,
        requested_by_user_id: UUID,
    ) -> None:
        self._session.add(
            AttendanceLocationException(
                attendance_id=attendance.id,
                location_evidence_id=evidence.id,
                requested_by_user_id=requested_by_user_id,
            )
        )
        await self._session.flush()

    async def _notify_super_admins_of_pending_location_review(
        self, attendance_id: UUID
    ) -> None:
        """Create one redacted in-app notice per Super Admin.

        The attendance workspace is the authorization boundary for the exact
        evidence. Notifications intentionally contain neither employee
        identity nor coordinate data, so they are safe in the bell and list
        views shared by the account.
        """
        super_admin_ids = tuple(
            (
                await self._session.scalars(
                    select(UserRole.user_id)
                    .join(Role, Role.id == UserRole.role_id)
                    .where(Role.code == "SUPER_ADMIN")
                    .distinct()
                )
            ).all()
        )
        if not super_admin_ids:
            return
        event_id = uuid5(
            NAMESPACE_URL,
            f"hr.attendance.location_review_required:{attendance_id}",
        )
        existing_user_ids = set(
            (
                await self._session.scalars(
                    select(Notification.user_id).where(
                        Notification.source_event_id == event_id,
                        Notification.user_id.in_(super_admin_ids),
                    )
                )
            ).all()
        )
        for user_id in super_admin_ids:
            if user_id in existing_user_ids:
                continue
            self._session.add(
                Notification(
                    user_id=user_id,
                    source_event_id=event_id,
                    type="HR_ATTENDANCE_LOCATION_REVIEW_REQUIRED",
                    title="Cần xác minh chấm công",
                    body=(
                        "Một lượt chấm công cần được xác minh vị trí trước khi "
                        "chốt trạng thái."
                    ),
                    data_json={
                        "attendanceId": str(attendance_id),
                        "actionPath": "/admin/attendance",
                    },
                    created_at=self._now(),
                )
            )

    async def list_attendance_worksites(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        search: str | None,
        worksite_status: AttendanceWorksiteStatus | None,
    ) -> tuple[tuple[AttendanceWorksiteData, ...], int]:
        self._require_attendance_configuration_admin(principal)
        criteria = []
        if search:
            pattern = f"%{search.strip()}%"
            criteria.append(
                or_(
                    AttendanceWorksite.code.ilike(pattern),
                    AttendanceWorksite.name.ilike(pattern),
                )
            )
        if worksite_status is not None:
            criteria.append(AttendanceWorksite.status == worksite_status)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(AttendanceWorksite).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(AttendanceWorksite)
                    .where(*criteria)
                    .order_by(AttendanceWorksite.name, AttendanceWorksite.code)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._attendance_worksite_data(row) for row in rows), total

    async def create_attendance_worksite(
        self,
        principal: AuthPrincipal,
        payload: CreateAttendanceWorksiteRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AttendanceWorksiteData:
        self._require_attendance_configuration_admin(principal)
        code = payload.code.upper()
        duplicate = await self._session.scalar(
            select(AttendanceWorksite.id).where(AttendanceWorksite.code == code)
        )
        if duplicate is not None:
            raise DomainError(
                code="HR_ATTENDANCE_WORKSITE_EXISTS",
                message="An attendance worksite with this code already exists.",
                status_code=409,
            )
        worksite = AttendanceWorksite(code=code, name=payload.name)
        self._session.add(worksite)
        await self._session.flush()
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.attendance_worksite.created",
            resource_type="attendance_worksite",
            resource_id=str(worksite.id),
            after=self._attendance_worksite_audit_snapshot(worksite),
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return self._attendance_worksite_data(worksite)

    async def update_attendance_worksite(
        self,
        principal: AuthPrincipal,
        worksite_id: UUID,
        payload: UpdateAttendanceWorksiteRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AttendanceWorksiteData:
        self._require_attendance_configuration_admin(principal)
        worksite = await self._session.scalar(
            select(AttendanceWorksite)
            .where(AttendanceWorksite.id == worksite_id)
            .with_for_update()
        )
        if worksite is None:
            raise DomainError(
                code="HR_ATTENDANCE_WORKSITE_NOT_FOUND",
                message="Attendance worksite not found.",
                status_code=404,
            )
        before = self._attendance_worksite_audit_snapshot(worksite)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(worksite, field, value)
        await self._session.flush()
        await self._session.refresh(worksite)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.attendance_worksite.updated",
            resource_type="attendance_worksite",
            resource_id=str(worksite.id),
            before=before,
            after=self._attendance_worksite_audit_snapshot(worksite),
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return self._attendance_worksite_data(worksite)

    async def list_attendance_worksite_policies(
        self,
        principal: AuthPrincipal,
        worksite_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[AttendanceWorksitePolicyData, ...], int]:
        self._require_attendance_configuration_admin(principal)
        exists = await self._session.scalar(
            select(AttendanceWorksite.id).where(AttendanceWorksite.id == worksite_id)
        )
        if exists is None:
            raise DomainError(
                code="HR_ATTENDANCE_WORKSITE_NOT_FOUND",
                message="Attendance worksite not found.",
                status_code=404,
            )
        criteria = (AttendanceWorksitePolicy.worksite_id == worksite_id,)
        total = int(
            await self._session.scalar(
                select(func.count())
                .select_from(AttendanceWorksitePolicy)
                .where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(AttendanceWorksitePolicy)
                    .where(*criteria)
                    .order_by(AttendanceWorksitePolicy.effective_from.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._attendance_policy_data(row) for row in rows), total

    async def create_attendance_worksite_policy(
        self,
        principal: AuthPrincipal,
        worksite_id: UUID,
        payload: CreateAttendanceWorksitePolicyRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AttendanceWorksitePolicyData:
        self._require_attendance_configuration_admin(principal)
        worksite = await self._session.scalar(
            select(AttendanceWorksite)
            .where(AttendanceWorksite.id == worksite_id)
            .with_for_update()
        )
        if worksite is None:
            raise DomainError(
                code="HR_ATTENDANCE_WORKSITE_NOT_FOUND",
                message="Attendance worksite not found.",
                status_code=404,
            )
        if worksite.status != AttendanceWorksiteStatus.ACTIVE:
            raise DomainError(
                code="HR_ATTENDANCE_WORKSITE_INACTIVE",
                message="An inactive worksite cannot receive a new policy.",
                status_code=409,
            )
        existing_timezone = await self._session.scalar(
            select(AttendanceWorksitePolicy.timezone)
            .where(AttendanceWorksitePolicy.worksite_id == worksite.id)
            .limit(1)
        )
        assignment_exists = await self._session.scalar(
            select(AttendanceAssignment.id)
            .where(AttendanceAssignment.worksite_id == worksite.id)
            .limit(1)
        )
        if (
            assignment_exists is not None
            and existing_timezone is not None
            and existing_timezone != payload.timezone
        ):
            raise DomainError(
                code="HR_ATTENDANCE_WORKSITE_TIMEZONE_LOCKED",
                message=(
                    "A worksite timezone cannot change after it has been assigned. "
                    "Create a new worksite for a physical relocation."
                ),
                status_code=409,
            )
        overlap = await self._session.scalar(
            select(AttendanceWorksitePolicy.id).where(
                AttendanceWorksitePolicy.worksite_id == worksite.id,
                *self._effective_range_overlap(
                    AttendanceWorksitePolicy,
                    effective_from=payload.effective_from,
                    effective_to=payload.effective_to,
                ),
            )
        )
        if overlap is not None:
            raise DomainError(
                code="HR_ATTENDANCE_POLICY_OVERLAP",
                message="This worksite already has a policy in that effective period.",
                status_code=409,
            )
        policy = AttendanceWorksitePolicy(
            worksite_id=worksite.id,
            **payload.model_dump(by_alias=False),
        )
        self._session.add(policy)
        await self._session.flush()
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.attendance_worksite_policy.created",
            resource_type="attendance_worksite_policy",
            resource_id=str(policy.id),
            after=self._attendance_policy_audit_snapshot(policy),
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return self._attendance_policy_data(policy)

    async def list_attendance_assignments(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        employee_id: UUID | None,
        worksite_id: UUID | None,
    ) -> tuple[tuple[AttendanceAssignmentData, ...], int]:
        self._require_attendance_configuration_admin(principal)
        criteria = []
        if employee_id is not None:
            criteria.append(AttendanceAssignment.employee_id == employee_id)
        if worksite_id is not None:
            criteria.append(AttendanceAssignment.worksite_id == worksite_id)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(AttendanceAssignment).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.execute(
                    select(
                        AttendanceAssignment,
                        Employee.employee_code,
                        Employee.full_name,
                        AttendanceWorksite.code,
                        AttendanceWorksite.name,
                    )
                    .join(Employee, Employee.id == AttendanceAssignment.employee_id)
                    .join(
                        AttendanceWorksite,
                        AttendanceWorksite.id == AttendanceAssignment.worksite_id,
                    )
                    .where(*criteria)
                    .order_by(
                        AttendanceAssignment.effective_from.desc(), Employee.full_name
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).tuples()
        )
        return (
            tuple(
                self._attendance_assignment_data(
                    row[0],
                    employee_code=row[1],
                    employee_name=row[2],
                    worksite_code=row[3],
                    worksite_name=row[4],
                )
                for row in rows
            ),
            total,
        )

    async def create_attendance_assignment(
        self,
        principal: AuthPrincipal,
        payload: CreateAttendanceAssignmentRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AttendanceAssignmentData:
        self._require_attendance_configuration_admin(principal)
        worksite = await self._session.scalar(
            select(AttendanceWorksite)
            .where(AttendanceWorksite.id == payload.worksite_id)
            .with_for_update()
        )
        if worksite is None:
            raise DomainError(
                code="HR_ATTENDANCE_WORKSITE_NOT_FOUND",
                message="Attendance worksite not found.",
                status_code=404,
            )
        if worksite.status != AttendanceWorksiteStatus.ACTIVE:
            raise DomainError(
                code="HR_ATTENDANCE_WORKSITE_INACTIVE",
                message="An inactive worksite cannot receive a new assignment.",
                status_code=409,
            )
        employee = await self._session.scalar(
            select(Employee).where(Employee.id == payload.employee_id).with_for_update()
        )
        if employee is None:
            raise DomainError(
                code="HR_EMPLOYEE_NOT_FOUND",
                message="Employee not found.",
                status_code=404,
            )
        policy_exists = await self._session.scalar(
            select(AttendanceWorksitePolicy.id).where(
                AttendanceWorksitePolicy.worksite_id == worksite.id,
                AttendanceWorksitePolicy.effective_from <= payload.effective_from,
                or_(
                    AttendanceWorksitePolicy.effective_to.is_(None),
                    AttendanceWorksitePolicy.effective_to >= payload.effective_from,
                ),
            )
        )
        if policy_exists is None:
            raise DomainError(
                code="HR_ATTENDANCE_ASSIGNMENT_POLICY_REQUIRED",
                message=(
                    "A worksite policy must be effective on the assignment start date."
                ),
                status_code=422,
            )
        overlap = await self._session.scalar(
            select(AttendanceAssignment.id).where(
                AttendanceAssignment.employee_id == employee.id,
                *self._effective_range_overlap(
                    AttendanceAssignment,
                    effective_from=payload.effective_from,
                    effective_to=payload.effective_to,
                ),
            )
        )
        if overlap is not None:
            raise DomainError(
                code="HR_ATTENDANCE_ASSIGNMENT_OVERLAP",
                message=(
                    "This employee already has an assignment in that effective period."
                ),
                status_code=409,
            )
        assignment = AttendanceAssignment(**payload.model_dump(by_alias=False))
        self._session.add(assignment)
        await self._session.flush()
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.attendance_assignment.created",
            resource_type="attendance_assignment",
            resource_id=str(assignment.id),
            after=self._attendance_assignment_audit_snapshot(assignment),
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return self._attendance_assignment_data(
            assignment,
            employee_code=employee.employee_code,
            employee_name=employee.full_name,
            worksite_code=worksite.code,
            worksite_name=worksite.name,
        )

    async def _self_employee(self, principal: AuthPrincipal) -> Employee:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="hr.attendance.self",
                compatible_roles=frozenset({"USER", "MODERATOR"}),
            ),
            lambda: DomainError(
                code="HR_ATTENDANCE_FORBIDDEN",
                message="You do not have permission to record attendance.",
                status_code=403,
            ),
        )
        employee = await self._session.scalar(
            select(Employee).where(Employee.user_id == principal.user_id)
        )
        if employee is None:
            raise DomainError(
                code="HR_EMPLOYEE_PROFILE_REQUIRED",
                message="No employee profile is linked to this account.",
                status_code=403,
            )
        return employee

    async def list_personal_attendance(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[AttendanceData, ...], int]:
        employee = await self._self_employee(principal)
        criteria = (Attendance.employee_id == employee.id,)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(Attendance).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(Attendance)
                    .where(*criteria)
                    .order_by(Attendance.work_date.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return (
            tuple(self._attendance_data(row, employee.full_name) for row in rows),
            total,
        )

    async def get_personal_attendance_workday_context(
        self, principal: AuthPrincipal
    ) -> AttendanceWorkdayContextData:
        """Return the active policy's server-owned IANA-local date.

        A missing policy is an expected configuration state for a newly linked
        employee. Ambiguous policies remain an error because the UI must not
        select a guessed workday.
        """
        employee = await self._self_employee(principal)
        try:
            policy, work_date = await self._resolve_attendance_location_policy(
                employee_id=employee.id, occurred_at=self._now()
            )
        except DomainError as error:
            if error.code != "HR_ATTENDANCE_LOCATION_POLICY_REQUIRED":
                raise
            return AttendanceWorkdayContextData(work_date=None, timezone=None)
        return AttendanceWorkdayContextData(
            work_date=work_date, timezone=policy.timezone
        )

    async def list_personal_attendance_location_evidence(
        self, principal: AuthPrincipal, attendance_id: UUID
    ) -> tuple[AttendanceLocationEvidenceReviewData, ...]:
        employee = await self._self_employee(principal)
        return await self._list_attendance_location_evidence(
            attendance_id=attendance_id, employee_id=employee.id
        )

    async def list_admin_attendance_location_evidence(
        self, principal: AuthPrincipal, attendance_id: UUID
    ) -> tuple[AttendanceLocationEvidenceReviewData, ...]:
        """Return exact evidence only to a Super Administrator."""
        self._require_attendance_configuration_admin(principal)
        return await self._list_attendance_location_evidence(
            attendance_id=attendance_id
        )

    async def purge_expired_attendance_locations(self) -> int:
        """Remove raw coordinates after their fixed 24-month retention period.

        Attendance and audit records remain, but neither the immutable evidence
        row nor its legacy attendance copy can retain an exact coordinate.
        """
        purged_at = self._now()
        async with self._session.begin():
            rows = tuple(
                (
                    await self._session.execute(
                        select(AttendanceLocationEvidence, Attendance)
                        .join(
                            Attendance,
                            Attendance.id == AttendanceLocationEvidence.attendance_id,
                        )
                        .where(
                            AttendanceLocationEvidence.retention_until <= purged_at,
                            AttendanceLocationEvidence.location_purged_at.is_(None),
                        )
                        .with_for_update()
                    )
                )
                .tuples()
                .all()
            )
            for evidence, attendance in rows:
                evidence.latitude = None
                evidence.longitude = None
                evidence.location_purged_at = purged_at
                if evidence.event_type == AttendanceLocationEventType.CHECK_IN:
                    attendance.check_in_latitude = None
                    attendance.check_in_longitude = None
                else:
                    attendance.check_out_latitude = None
                    attendance.check_out_longitude = None
            return len(rows)

    async def _list_attendance_location_evidence(
        self, *, attendance_id: UUID, employee_id: UUID | None = None
    ) -> tuple[AttendanceLocationEvidenceReviewData, ...]:
        criteria: list[ColumnElement[bool]] = [
            AttendanceLocationEvidence.attendance_id == attendance_id
        ]
        if employee_id is not None:
            criteria.append(Attendance.employee_id == employee_id)
        rows = (
            await self._session.execute(
                select(
                    AttendanceLocationEvidence,
                    AttendanceWorksitePolicy,
                    AttendanceWorksite,
                )
                .join(
                    Attendance,
                    Attendance.id == AttendanceLocationEvidence.attendance_id,
                )
                .join(
                    AttendanceWorksitePolicy,
                    AttendanceWorksitePolicy.id
                    == AttendanceLocationEvidence.worksite_policy_id,
                )
                .join(
                    AttendanceWorksite,
                    AttendanceWorksite.id == AttendanceWorksitePolicy.worksite_id,
                )
                .where(
                    *criteria,
                )
                .order_by(AttendanceLocationEvidence.event_type)
            )
        ).tuples()
        return tuple(
            self._location_evidence_review_data(
                row[0], worksite_code=row[2].code, worksite_name=row[2].name
            )
            for row in rows
        )

    async def check_in(
        self,
        principal: AuthPrincipal,
        payload: CheckInRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AttendanceData:
        employee = await self._self_employee(principal)
        now = self._now()
        policy, work_date = await self._resolve_attendance_location_policy(
            employee_id=employee.id, occurred_at=now
        )
        existing = await self._session.scalar(
            select(Attendance).where(
                Attendance.employee_id == employee.id,
                Attendance.work_date == work_date,
            )
        )
        if existing is not None:
            raise DomainError(
                code="HR_ATTENDANCE_ALREADY_CHECKED_IN",
                message="You have already checked in today.",
                status_code=409,
            )
        outcome, distance_meters = self._location_outcome(
            payload=payload, policy=policy
        )
        attendance = Attendance(
            employee_id=employee.id,
            work_date=work_date,
            check_in_at=now,
            note=payload.note,
            status=(
                AttendanceStatus.PRESENT
                if outcome == AttendanceLocationOutcome.ACCEPTED
                else AttendanceStatus.PENDING
            ),
        )
        self._session.add(attendance)
        await self._session.flush()
        evidence = await self._record_attendance_location_evidence(
            attendance=attendance,
            event_type=AttendanceLocationEventType.CHECK_IN,
            policy=policy,
            payload=payload,
            distance_meters=distance_meters,
            outcome=outcome,
            received_at=now,
        )
        if outcome != AttendanceLocationOutcome.ACCEPTED:
            await self._create_pending_location_exception(
                attendance=attendance,
                evidence=evidence,
                requested_by_user_id=principal.user_id,
            )
            await self._notify_super_admins_of_pending_location_review(attendance.id)
        await self._session.refresh(attendance)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.attendance.checked_in",
            resource_type="attendance",
            resource_id=str(attendance.id),
            after={
                "work_date": attendance.work_date.isoformat(),
                "status": attendance.status.value,
                "location_outcome": outcome.value,
                "worksite_policy_id": str(policy.id),
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._attendance_data(attendance, employee.full_name)
        await self._session.commit()
        return data

    async def check_out(
        self,
        principal: AuthPrincipal,
        payload: CheckOutRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AttendanceData:
        employee = await self._self_employee(principal)
        now = self._now()
        policy, work_date = await self._resolve_attendance_location_policy(
            employee_id=employee.id, occurred_at=now
        )
        attendance = await self._session.scalar(
            select(Attendance).where(
                Attendance.employee_id == employee.id,
                Attendance.work_date == work_date,
            )
        )
        if attendance is None:
            raise DomainError(
                code="HR_ATTENDANCE_CHECK_IN_REQUIRED",
                message="Check in before checking out.",
                status_code=409,
            )
        if attendance.check_out_at is not None:
            raise DomainError(
                code="HR_ATTENDANCE_ALREADY_CHECKED_OUT",
                message="You have already checked out today.",
                status_code=409,
            )
        if attendance.status == AttendanceStatus.REJECTED:
            raise DomainError(
                code="HR_ATTENDANCE_LOCATION_REJECTED",
                message="A rejected attendance exception cannot be checked out.",
                status_code=409,
            )
        outcome, distance_meters = self._location_outcome(
            payload=payload, policy=policy
        )
        attendance.check_out_at = now
        if outcome != AttendanceLocationOutcome.ACCEPTED:
            attendance.status = AttendanceStatus.PENDING
        await self._session.flush()
        evidence = await self._record_attendance_location_evidence(
            attendance=attendance,
            event_type=AttendanceLocationEventType.CHECK_OUT,
            policy=policy,
            payload=payload,
            distance_meters=distance_meters,
            outcome=outcome,
            received_at=now,
        )
        if outcome != AttendanceLocationOutcome.ACCEPTED:
            await self._create_pending_location_exception(
                attendance=attendance,
                evidence=evidence,
                requested_by_user_id=principal.user_id,
            )
            await self._notify_super_admins_of_pending_location_review(attendance.id)
        await self._session.refresh(attendance)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.attendance.checked_out",
            resource_type="attendance",
            resource_id=str(attendance.id),
            after={
                "work_date": attendance.work_date.isoformat(),
                "status": attendance.status.value,
                "location_outcome": outcome.value,
                "worksite_policy_id": str(policy.id),
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._attendance_data(attendance, employee.full_name)
        await self._session.commit()
        return data

    async def decide_attendance_location_exception(
        self,
        principal: AuthPrincipal,
        exception_id: UUID,
        payload: AttendanceLocationExceptionDecisionRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AttendanceLocationExceptionData:
        self._require(principal, "hr.attendance.adjust")
        exception = await self._session.scalar(
            select(AttendanceLocationException)
            .where(AttendanceLocationException.id == exception_id)
            .with_for_update()
        )
        if exception is None:
            raise DomainError(
                code="HR_ATTENDANCE_LOCATION_EXCEPTION_NOT_FOUND",
                message="Attendance location exception not found.",
                status_code=404,
            )
        if exception.status != AttendanceLocationExceptionStatus.PENDING:
            raise DomainError(
                code="HR_ATTENDANCE_LOCATION_EXCEPTION_ALREADY_DECIDED",
                message="Attendance location exception has already been decided.",
                status_code=409,
            )
        attendance = await self._session.scalar(
            select(Attendance)
            .where(Attendance.id == exception.attendance_id)
            .with_for_update()
        )
        if attendance is None:
            raise DomainError(
                code="HR_ATTENDANCE_NOT_FOUND",
                message="Attendance record not found.",
                status_code=404,
            )
        evidence = await self._session.get(
            AttendanceLocationEvidence, exception.location_evidence_id
        )
        if evidence is None or evidence.attendance_id != attendance.id:
            raise DomainError(
                code="HR_ATTENDANCE_LOCATION_EXCEPTION_INVALID",
                message="Attendance location exception evidence is invalid.",
                status_code=409,
            )

        exception.status = payload.status
        exception.decision_note = payload.decision_note
        exception.reviewed_by_user_id = principal.user_id
        exception.reviewed_at = self._now()

        if payload.status == AttendanceLocationExceptionStatus.REJECTED:
            attendance.status = AttendanceStatus.REJECTED
        else:
            remaining_exception_statuses = tuple(
                (
                    await self._session.scalars(
                        select(AttendanceLocationException.status).where(
                            AttendanceLocationException.attendance_id == attendance.id,
                            AttendanceLocationException.id != exception.id,
                        )
                    )
                ).all()
            )
            if (
                AttendanceLocationExceptionStatus.REJECTED
                in remaining_exception_statuses
            ):
                attendance.status = AttendanceStatus.REJECTED
            elif (
                AttendanceLocationExceptionStatus.PENDING
                in remaining_exception_statuses
            ):
                attendance.status = AttendanceStatus.PENDING
            else:
                attendance.status = AttendanceStatus.PRESENT

        await self._session.flush()
        await self._session.refresh(exception)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.attendance_location_exception.decided",
            resource_type="attendance_location_exception",
            resource_id=str(exception.id),
            after={
                "attendance_id": str(attendance.id),
                "location_evidence_id": str(exception.location_evidence_id),
                "decision": exception.status.value,
                "attendance_status": attendance.status.value,
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        data = AttendanceLocationExceptionData.model_validate(exception)
        await self._session.commit()
        return data

    @staticmethod
    def _location_evidence_review_data(
        evidence: AttendanceLocationEvidence,
        *,
        worksite_code: str,
        worksite_name: str,
    ) -> AttendanceLocationEvidenceReviewData:
        coordinates_available = not HrService._location_evidence_has_expired(evidence)
        return AttendanceLocationEvidenceReviewData.model_validate(
            {
                **{
                    field: getattr(evidence, field)
                    for field in AttendanceLocationEvidenceReviewData.model_fields
                    if field not in {"worksite_code", "worksite_name"}
                },
                "worksite_code": worksite_code,
                "worksite_name": worksite_name,
                "latitude": evidence.latitude if coordinates_available else None,
                "longitude": evidence.longitude if coordinates_available else None,
            }
        )

    @staticmethod
    def _admin_location_exception_data(
        exception: AttendanceLocationException,
        *,
        attendance: Attendance,
        evidence: AttendanceLocationEvidence,
        employee_code: str,
        employee_name: str,
        worksite_code: str,
        worksite_name: str,
    ) -> AdminAttendanceLocationExceptionData:
        return AdminAttendanceLocationExceptionData(
            id=exception.id,
            attendance_id=exception.attendance_id,
            location_evidence_id=exception.location_evidence_id,
            status=exception.status,
            requested_by_user_id=exception.requested_by_user_id,
            decision_note=exception.decision_note,
            reviewed_by_user_id=exception.reviewed_by_user_id,
            reviewed_at=exception.reviewed_at,
            created_at=exception.created_at,
            updated_at=exception.updated_at,
            employee_id=attendance.employee_id,
            employee_code=employee_code,
            employee_name=employee_name,
            work_date=attendance.work_date,
            attendance_status=attendance.status,
            evidence=HrService._location_evidence_review_data(
                evidence,
                worksite_code=worksite_code,
                worksite_name=worksite_name,
            ),
        )

    async def list_attendance_location_exceptions(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        exception_status: AttendanceLocationExceptionStatus | None,
    ) -> tuple[tuple[AdminAttendanceLocationExceptionData, ...], int]:
        # This projection intentionally exposes exact evidence only to Super
        # Admins; every other HR endpoint remains coordinate-free.
        self._require_attendance_configuration_admin(principal)
        criteria: list[ColumnElement[bool]] = []
        if exception_status is not None:
            criteria.append(AttendanceLocationException.status == exception_status)
        total = int(
            await self._session.scalar(
                select(func.count())
                .select_from(AttendanceLocationException)
                .where(*criteria)
            )
            or 0
        )
        rows = (
            await self._session.execute(
                select(
                    AttendanceLocationException,
                    Attendance,
                    AttendanceLocationEvidence,
                    Employee.employee_code,
                    Employee.full_name,
                    AttendanceWorksite.code,
                    AttendanceWorksite.name,
                )
                .join(
                    Attendance,
                    Attendance.id == AttendanceLocationException.attendance_id,
                )
                .join(
                    AttendanceLocationEvidence,
                    AttendanceLocationEvidence.id
                    == AttendanceLocationException.location_evidence_id,
                )
                .join(
                    AttendanceWorksitePolicy,
                    AttendanceWorksitePolicy.id
                    == AttendanceLocationEvidence.worksite_policy_id,
                )
                .join(
                    AttendanceWorksite,
                    AttendanceWorksite.id == AttendanceWorksitePolicy.worksite_id,
                )
                .join(Employee, Employee.id == Attendance.employee_id)
                .where(*criteria)
                .order_by(
                    AttendanceLocationException.created_at.desc(),
                    AttendanceLocationException.id,
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).tuples()
        return (
            tuple(
                self._admin_location_exception_data(
                    row[0],
                    attendance=row[1],
                    evidence=row[2],
                    employee_code=row[3],
                    employee_name=row[4],
                    worksite_code=row[5],
                    worksite_name=row[6],
                )
                for row in rows
            ),
            total,
        )

    async def _self_leave_employee(self, principal: AuthPrincipal) -> Employee:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="hr.leave.self",
                compatible_roles=frozenset({"USER", "MODERATOR"}),
            ),
            lambda: DomainError(
                code="HR_LEAVE_FORBIDDEN",
                message="You do not have permission to manage leave requests.",
                status_code=403,
            ),
        )
        employee = await self._session.scalar(
            select(Employee).where(Employee.user_id == principal.user_id)
        )
        if employee is None:
            raise DomainError(
                code="HR_EMPLOYEE_PROFILE_REQUIRED",
                message="No employee profile is linked to this account.",
                status_code=403,
            )
        return employee

    @staticmethod
    def _leave_data(request: LeaveRequest, employee_name: str) -> LeaveRequestData:
        return LeaveRequestData.model_validate(
            {
                **{
                    field: getattr(request, field)
                    for field in LeaveRequestData.model_fields
                    if field != "employee_name"
                },
                "employee_name": employee_name,
            }
        )

    @staticmethod
    def _admin_leave_data(
        request: LeaveRequest,
        *,
        employee_code: str,
        employee_name: str,
        department_name: str,
    ) -> AdminLeaveRequestData:
        return AdminLeaveRequestData.model_validate(
            {
                **HrService._leave_data(request, employee_name).model_dump(
                    by_alias=False
                ),
                "employee_code": employee_code,
                "department_name": department_name,
            }
        )

    @staticmethod
    def _leave_audit_snapshot(request: LeaveRequest) -> dict[str, object]:
        return {
            "employee_id": str(request.employee_id),
            "status": request.status.value,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
        }

    async def list_personal_leave_requests(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[LeaveRequestData, ...], int]:
        employee = await self._self_leave_employee(principal)
        criteria = (LeaveRequest.employee_id == employee.id,)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(LeaveRequest).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(LeaveRequest)
                    .where(*criteria)
                    .order_by(LeaveRequest.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._leave_data(row, employee.full_name) for row in rows), total

    async def _notify_super_admins_of_hr_request(
        self, request: LeaveRequest | OvertimeRequest
    ) -> None:
        """Persist redacted notices in the request's transaction; never send email."""
        is_leave = isinstance(request, LeaveRequest)
        kind = "leave" if is_leave else "overtime"
        request_key = "leaveRequestId" if is_leave else "overtimeRequestId"
        event_id = uuid5(NAMESPACE_URL, f"hr.{kind}.created:{request.id}")
        existing_recipients = select(Notification.user_id).where(
            Notification.source_event_id == event_id
        )
        recipients = await self._session.scalars(
            select(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.code == "SUPER_ADMIN",
                User.status == UserStatus.ACTIVE,
                User.disabled_at.is_(None),
                User.deleted_at.is_(None),
                User.id.not_in(existing_recipients),
            )
            .distinct()
        )
        for user_id in recipients:
            self._session.add(
                Notification(
                    user_id=user_id,
                    source_event_id=event_id,
                    type=f"HR_{kind.upper()}_REQUEST_CREATED",
                    title="Đơn nghỉ phép mới" if is_leave else "Yêu cầu tăng ca mới",
                    body=(
                        "Có đơn nghỉ phép mới cần xét duyệt."
                        if is_leave
                        else "Có yêu cầu tăng ca mới cần xét duyệt."
                    ),
                    data_json={
                        request_key: str(request.id),
                        "actionPath": f"/admin/{kind}",
                    },
                    created_at=self._now(),
                )
            )
        await self._session.flush()

    async def create_leave_request(
        self,
        principal: AuthPrincipal,
        payload: CreateLeaveRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> LeaveRequestData:
        employee = await self._self_leave_employee(principal)
        # Serialize leave submissions for one employee before checking inclusive dates.
        await self._session.scalar(
            select(Employee.id).where(Employee.id == employee.id).with_for_update()
        )
        overlapping_request_id = await self._session.scalar(
            select(LeaveRequest.id)
            .where(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.status.in_(
                    (LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED)
                ),
                LeaveRequest.start_date <= payload.end_date,
                LeaveRequest.end_date >= payload.start_date,
            )
            .limit(1)
        )
        if overlapping_request_id is not None:
            raise DomainError(
                code="HR_LEAVE_DATE_OVERLAP",
                message="This leave period overlaps an active request.",
                status_code=409,
            )
        request = LeaveRequest(
            employee_id=employee.id,
            leave_type=payload.leave_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            reason=payload.reason,
        )
        self._session.add(request)
        await self._session.flush()
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.leave.created",
            resource_type="leave_request",
            resource_id=str(request.id),
            after=self._leave_audit_snapshot(request),
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._notify_super_admins_of_hr_request(request)
        data = self._leave_data(request, employee.full_name)
        await self._session.commit()
        return data

    async def cancel_leave_request(
        self,
        principal: AuthPrincipal,
        leave_request_id: UUID,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> LeaveRequestData:
        employee = await self._self_leave_employee(principal)
        request = await self._session.scalar(
            select(LeaveRequest)
            .where(
                LeaveRequest.id == leave_request_id,
                LeaveRequest.employee_id == employee.id,
            )
            .with_for_update()
        )
        if request is None:
            raise DomainError(
                code="HR_LEAVE_REQUEST_NOT_FOUND",
                message="Leave request not found.",
                status_code=404,
            )
        if request.status != LeaveRequestStatus.PENDING:
            raise DomainError(
                code="HR_LEAVE_CANCEL_INVALID",
                message="Only pending leave requests can be cancelled.",
                status_code=409,
            )
        before = self._leave_audit_snapshot(request)
        request.status = LeaveRequestStatus.CANCELLED
        await self._session.flush()
        await self._session.refresh(request)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.leave.cancelled",
            resource_type="leave_request",
            resource_id=str(request.id),
            before=before,
            after=self._leave_audit_snapshot(request),
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._leave_data(request, employee.full_name)
        await self._session.commit()
        return data

    async def list_admin_leave_requests(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        search: str | None,
        department_id: UUID | None,
        leave_status: LeaveRequestStatus | None,
        start_date_from: date | None,
        start_date_to: date | None,
    ) -> tuple[tuple[AdminLeaveRequestData, ...], int]:
        self._require(principal, "hr.leave.read")
        if (
            start_date_from is not None
            and start_date_to is not None
            and start_date_from > start_date_to
        ):
            raise DomainError(
                code="HR_LEAVE_DATE_RANGE_INVALID",
                message="Leave start date must not be after leave end date.",
                status_code=422,
            )
        criteria = []
        if search:
            pattern = f"%{search.strip()}%"
            criteria.append(
                or_(
                    Employee.employee_code.ilike(pattern),
                    Employee.full_name.ilike(pattern),
                    Employee.email.ilike(pattern),
                )
            )
        if department_id:
            criteria.append(Employee.department_id == department_id)
        if leave_status:
            criteria.append(LeaveRequest.status == leave_status)
        if start_date_from:
            criteria.append(LeaveRequest.start_date >= start_date_from)
        if start_date_to:
            criteria.append(LeaveRequest.start_date <= start_date_to)
        total = int(
            await self._session.scalar(
                select(func.count())
                .select_from(LeaveRequest)
                .join(Employee, Employee.id == LeaveRequest.employee_id)
                .where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.execute(
                    select(
                        LeaveRequest,
                        Employee.employee_code,
                        Employee.full_name,
                        Department.name,
                    )
                    .join(Employee, Employee.id == LeaveRequest.employee_id)
                    .join(Department, Department.id == Employee.department_id)
                    .where(*criteria)
                    .order_by(LeaveRequest.created_at.desc(), Employee.full_name)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).tuples()
        )
        return (
            tuple(
                self._admin_leave_data(
                    row[0],
                    employee_code=row[1],
                    employee_name=row[2],
                    department_name=row[3],
                )
                for row in rows
            ),
            total,
        )

    async def decide_leave_request(
        self,
        principal: AuthPrincipal,
        leave_request_id: UUID,
        decision: LeaveRequestStatus,
        payload: LeaveDecisionRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AdminLeaveRequestData:
        self._require(principal, "hr.leave.manage")
        if decision not in {LeaveRequestStatus.APPROVED, LeaveRequestStatus.REJECTED}:
            raise ValueError("Leave requests can only be approved or rejected.")
        request = await self._session.scalar(
            select(LeaveRequest)
            .where(LeaveRequest.id == leave_request_id)
            .with_for_update()
        )
        if request is None:
            raise DomainError(
                code="HR_LEAVE_REQUEST_NOT_FOUND",
                message="Leave request not found.",
                status_code=404,
            )
        if request.status != LeaveRequestStatus.PENDING:
            raise DomainError(
                code="HR_LEAVE_DECISION_INVALID",
                message="Only pending leave requests can be decided.",
                status_code=409,
            )
        employee = await self._session.get(Employee, request.employee_id)
        if employee is None:
            raise DomainError(
                code="HR_EMPLOYEE_NOT_FOUND",
                message="Employee not found.",
                status_code=404,
            )
        before = self._leave_audit_snapshot(request)
        request.status = decision
        request.decision_note = payload.decision_note
        request.reviewed_by_user_id = principal.user_id
        request.reviewed_at = self._now()
        await self._session.flush()
        await self._session.refresh(request)
        audit.record(
            actor_user_id=principal.user_id,
            action=f"hr.leave.{decision.value.lower()}",
            resource_type="leave_request",
            resource_id=str(request.id),
            before=before,
            after=self._leave_audit_snapshot(request),
            request_id=request_id,
            user_agent=user_agent,
        )
        if employee.user_id is not None:
            event_id = uuid5(
                NAMESPACE_URL,
                f"hr.leave.decision:{request.id}:{decision.value}",
            )
            existing_notification = await self._session.scalar(
                select(Notification.id).where(
                    Notification.user_id == employee.user_id,
                    Notification.source_event_id == event_id,
                )
            )
            if existing_notification is None:
                outcome = (
                    "đã được duyệt"
                    if decision == LeaveRequestStatus.APPROVED
                    else "đã bị từ chối"
                )
                self._session.add(
                    Notification(
                        user_id=employee.user_id,
                        source_event_id=event_id,
                        type="HR_LEAVE_DECISION",
                        title="Cập nhật đơn nghỉ phép",
                        body=f"Đơn nghỉ phép của bạn {outcome}.",
                        data_json={
                            "leaveRequestId": str(request.id),
                            "status": decision.value,
                        },
                        created_at=self._now(),
                    )
                )
        data = self._admin_leave_data(
            request,
            employee_code=employee.employee_code,
            employee_name=employee.full_name,
            department_name=str(
                await self._session.scalar(
                    select(Department.name).where(
                        Department.id == employee.department_id
                    )
                )
            ),
        )
        await self._session.commit()
        return data

    async def _self_overtime_employee(self, principal: AuthPrincipal) -> Employee:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="hr.overtime.self",
                compatible_roles=frozenset({"USER", "MODERATOR"}),
            ),
            lambda: DomainError(
                code="HR_OVERTIME_FORBIDDEN",
                message="You do not have permission to manage overtime requests.",
                status_code=403,
            ),
        )
        employee = await self._session.scalar(
            select(Employee).where(Employee.user_id == principal.user_id)
        )
        if employee is None:
            raise DomainError(
                code="HR_EMPLOYEE_PROFILE_REQUIRED",
                message="No employee profile is linked to this account.",
                status_code=403,
            )
        return employee

    @staticmethod
    def _overtime_data(
        request: OvertimeRequest, employee_name: str
    ) -> OvertimeRequestData:
        return OvertimeRequestData.model_validate(
            {
                **{
                    field: getattr(request, field)
                    for field in OvertimeRequestData.model_fields
                    if field != "employee_name"
                },
                "employee_name": employee_name,
            }
        )

    @staticmethod
    def _admin_overtime_data(
        request: OvertimeRequest,
        *,
        employee_code: str,
        employee_name: str,
        department_name: str,
    ) -> AdminOvertimeRequestData:
        return AdminOvertimeRequestData.model_validate(
            {
                **HrService._overtime_data(request, employee_name).model_dump(
                    by_alias=False
                ),
                "employee_code": employee_code,
                "department_name": department_name,
            }
        )

    @staticmethod
    def _overtime_audit_snapshot(request: OvertimeRequest) -> dict[str, object]:
        return {
            "employee_id": str(request.employee_id),
            "status": request.status.value,
            "start_at": request.start_at.isoformat(),
            "end_at": request.end_at.isoformat(),
        }

    async def list_personal_overtime_requests(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[OvertimeRequestData, ...], int]:
        employee = await self._self_overtime_employee(principal)
        criteria = (OvertimeRequest.employee_id == employee.id,)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(OvertimeRequest).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(OvertimeRequest)
                    .where(*criteria)
                    .order_by(OvertimeRequest.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return (
            tuple(self._overtime_data(row, employee.full_name) for row in rows),
            total,
        )

    async def create_overtime_request(
        self,
        principal: AuthPrincipal,
        payload: CreateOvertimeRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> OvertimeRequestData:
        employee = await self._self_overtime_employee(principal)
        await self._session.scalar(
            select(Employee.id).where(Employee.id == employee.id).with_for_update()
        )
        overlapping_request_id = await self._session.scalar(
            select(OvertimeRequest.id)
            .where(
                OvertimeRequest.employee_id == employee.id,
                OvertimeRequest.status.in_(
                    (OvertimeRequestStatus.PENDING, OvertimeRequestStatus.APPROVED)
                ),
                OvertimeRequest.start_at < payload.end_at,
                OvertimeRequest.end_at > payload.start_at,
            )
            .limit(1)
        )
        if overlapping_request_id is not None:
            raise DomainError(
                code="HR_OVERTIME_INTERVAL_OVERLAP",
                message="This overtime period overlaps an active request.",
                status_code=409,
            )
        request = OvertimeRequest(
            employee_id=employee.id,
            start_at=payload.start_at,
            end_at=payload.end_at,
            reason=payload.reason,
        )
        self._session.add(request)
        await self._session.flush()
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.overtime.created",
            resource_type="overtime_request",
            resource_id=str(request.id),
            after=self._overtime_audit_snapshot(request),
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._notify_super_admins_of_hr_request(request)
        data = self._overtime_data(request, employee.full_name)
        await self._session.commit()
        return data

    async def cancel_overtime_request(
        self,
        principal: AuthPrincipal,
        overtime_request_id: UUID,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> OvertimeRequestData:
        employee = await self._self_overtime_employee(principal)
        request = await self._session.scalar(
            select(OvertimeRequest)
            .where(
                OvertimeRequest.id == overtime_request_id,
                OvertimeRequest.employee_id == employee.id,
            )
            .with_for_update()
        )
        if request is None:
            raise DomainError(
                code="HR_OVERTIME_REQUEST_NOT_FOUND",
                message="Overtime request not found.",
                status_code=404,
            )
        if request.status != OvertimeRequestStatus.PENDING:
            raise DomainError(
                code="HR_OVERTIME_CANCEL_INVALID",
                message="Only pending overtime requests can be cancelled.",
                status_code=409,
            )
        before = self._overtime_audit_snapshot(request)
        request.status = OvertimeRequestStatus.CANCELLED
        await self._session.flush()
        await self._session.refresh(request)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.overtime.cancelled",
            resource_type="overtime_request",
            resource_id=str(request.id),
            before=before,
            after=self._overtime_audit_snapshot(request),
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._overtime_data(request, employee.full_name)
        await self._session.commit()
        return data

    async def list_admin_overtime_requests(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        search: str | None,
        department_id: UUID | None,
        overtime_status: OvertimeRequestStatus | None,
        start_at_from: datetime | None,
        start_at_to: datetime | None,
    ) -> tuple[tuple[AdminOvertimeRequestData, ...], int]:
        self._require(principal, "hr.overtime.read")
        if any(
            value is not None and value.utcoffset() is None
            for value in (start_at_from, start_at_to)
        ):
            raise DomainError(
                code="HR_OVERTIME_TIMEZONE_REQUIRED",
                message="Overtime filter datetimes must include a timezone offset.",
                status_code=422,
            )
        if (
            start_at_from is not None
            and start_at_to is not None
            and start_at_from > start_at_to
        ):
            raise DomainError(
                code="HR_OVERTIME_TIME_RANGE_INVALID",
                message="Overtime start must not be after overtime end.",
                status_code=422,
            )
        criteria = []
        if search:
            pattern = f"%{search.strip()}%"
            criteria.append(
                or_(
                    Employee.employee_code.ilike(pattern),
                    Employee.full_name.ilike(pattern),
                    Employee.email.ilike(pattern),
                )
            )
        if department_id:
            criteria.append(Employee.department_id == department_id)
        if overtime_status:
            criteria.append(OvertimeRequest.status == overtime_status)
        if start_at_from:
            criteria.append(OvertimeRequest.start_at >= start_at_from)
        if start_at_to:
            criteria.append(OvertimeRequest.start_at <= start_at_to)
        total = int(
            await self._session.scalar(
                select(func.count())
                .select_from(OvertimeRequest)
                .join(Employee, Employee.id == OvertimeRequest.employee_id)
                .where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.execute(
                    select(
                        OvertimeRequest,
                        Employee.employee_code,
                        Employee.full_name,
                        Department.name,
                    )
                    .join(Employee, Employee.id == OvertimeRequest.employee_id)
                    .join(Department, Department.id == Employee.department_id)
                    .where(*criteria)
                    .order_by(OvertimeRequest.created_at.desc(), Employee.full_name)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).tuples()
        )
        return (
            tuple(
                self._admin_overtime_data(
                    row[0],
                    employee_code=row[1],
                    employee_name=row[2],
                    department_name=row[3],
                )
                for row in rows
            ),
            total,
        )

    async def decide_overtime_request(
        self,
        principal: AuthPrincipal,
        overtime_request_id: UUID,
        decision: OvertimeRequestStatus,
        payload: OvertimeDecisionRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> AdminOvertimeRequestData:
        self._require(principal, "hr.overtime.manage")
        if decision not in {
            OvertimeRequestStatus.APPROVED,
            OvertimeRequestStatus.REJECTED,
        }:
            raise ValueError("Overtime requests can only be approved or rejected.")
        request = await self._session.scalar(
            select(OvertimeRequest)
            .where(OvertimeRequest.id == overtime_request_id)
            .with_for_update()
        )
        if request is None:
            raise DomainError(
                code="HR_OVERTIME_REQUEST_NOT_FOUND",
                message="Overtime request not found.",
                status_code=404,
            )
        if request.status != OvertimeRequestStatus.PENDING:
            raise DomainError(
                code="HR_OVERTIME_DECISION_INVALID",
                message="Only pending overtime requests can be decided.",
                status_code=409,
            )
        employee = await self._session.get(Employee, request.employee_id)
        if employee is None:
            raise DomainError(
                code="HR_EMPLOYEE_NOT_FOUND",
                message="Employee not found.",
                status_code=404,
            )
        before = self._overtime_audit_snapshot(request)
        request.status = decision
        request.decision_note = payload.decision_note
        request.reviewed_by_user_id = principal.user_id
        request.reviewed_at = self._now()
        await self._session.flush()
        await self._session.refresh(request)
        audit.record(
            actor_user_id=principal.user_id,
            action=f"hr.overtime.{decision.value.lower()}",
            resource_type="overtime_request",
            resource_id=str(request.id),
            before=before,
            after=self._overtime_audit_snapshot(request),
            request_id=request_id,
            user_agent=user_agent,
        )
        if employee.user_id is not None:
            event_id = uuid5(
                NAMESPACE_URL,
                f"hr.overtime.decision:{request.id}:{decision.value}",
            )
            existing_notification = await self._session.scalar(
                select(Notification.id).where(
                    Notification.user_id == employee.user_id,
                    Notification.source_event_id == event_id,
                )
            )
            if existing_notification is None:
                outcome = (
                    "đã được duyệt"
                    if decision == OvertimeRequestStatus.APPROVED
                    else "đã bị từ chối"
                )
                self._session.add(
                    Notification(
                        user_id=employee.user_id,
                        source_event_id=event_id,
                        type="HR_OVERTIME_DECISION",
                        title="Cập nhật yêu cầu tăng ca",
                        body=f"Yêu cầu tăng ca của bạn {outcome}.",
                        data_json={
                            "overtimeRequestId": str(request.id),
                            "status": decision.value,
                        },
                        created_at=self._now(),
                    )
                )
        department_name = await self._session.scalar(
            select(Department.name).where(Department.id == employee.department_id)
        )
        data = self._admin_overtime_data(
            request,
            employee_code=employee.employee_code,
            employee_name=employee.full_name,
            department_name=str(department_name),
        )
        await self._session.commit()
        return data
