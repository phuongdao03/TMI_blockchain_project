from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import (
    Attendance,
    AttendanceAssignment,
    AttendanceStatus,
    AttendanceWorksite,
    AttendanceWorksitePolicy,
    Employee,
    OvertimeRequest,
    OvertimeRequestStatus,
    PayrollEntry,
    PayrollPeriod,
    PayrollPeriodStatus,
)
from app.modules.hr.payroll import (
    OvertimeInterval,
    PayrollCalculationInput,
    approved_overtime_hours_for_local_month,
    calculate_payroll,
    local_month_bounds,
    round_vnd,
)
from app.modules.hr.schemas import (
    CreatePayrollPeriodRequest,
    PayrollEntryData,
    PayrollPeriodData,
    PayrollPeriodDetailData,
    UpdatePayrollEntryRequest,
)

PAYABLE_ATTENDANCE_WEIGHTS = {
    AttendanceStatus.PRESENT: Decimal("1"),
    AttendanceStatus.LATE: Decimal("1"),
    AttendanceStatus.HALF_DAY: Decimal("0.5"),
}


class PayrollService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _require_super_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_resource_scope(
            "SUPER_ADMIN" in principal.roles,
            lambda: DomainError(
                code="HR_PAYROLL_FORBIDDEN",
                message="Only a super administrator can manage payroll.",
                status_code=403,
            ),
        )

    @staticmethod
    def _period_data(period: PayrollPeriod) -> PayrollPeriodData:
        return PayrollPeriodData.model_validate(period)

    @staticmethod
    def _entry_data(entry: PayrollEntry) -> PayrollEntryData:
        return PayrollEntryData.model_validate(entry)

    @classmethod
    def _period_detail_data(
        cls, period: PayrollPeriod, entries: tuple[PayrollEntry, ...]
    ) -> PayrollPeriodDetailData:
        return PayrollPeriodDetailData.model_validate(
            {
                **cls._period_data(period).model_dump(by_alias=False),
                "entries": tuple(cls._entry_data(entry) for entry in entries),
            }
        )

    @staticmethod
    def _period_end(period_month: date) -> date:
        return date(
            period_month.year,
            period_month.month,
            monthrange(period_month.year, period_month.month)[1],
        )

    async def _payroll_timezone(self, period: PayrollPeriod) -> str:
        period_end = self._period_end(period.period_month)
        policies = tuple(
            (
                await self._session.scalars(
                    select(AttendanceWorksitePolicy).where(
                        AttendanceWorksitePolicy.worksite_id == period.worksite_id,
                        AttendanceWorksitePolicy.effective_from <= period_end,
                        or_(
                            AttendanceWorksitePolicy.effective_to.is_(None),
                            AttendanceWorksitePolicy.effective_to
                            >= period.period_month,
                        ),
                    )
                )
            ).all()
        )
        timezones = {policy.timezone for policy in policies}
        if len(timezones) != 1:
            raise DomainError(
                code="HR_PAYROLL_WORKSITE_TIMEZONE_REQUIRED",
                message=(
                    "Exactly one worksite timezone must apply to the payroll month."
                ),
                status_code=422,
            )
        return timezones.pop()

    async def _eligible_employees(self, period: PayrollPeriod) -> tuple[Employee, ...]:
        period_end = self._period_end(period.period_month)
        assigned_employee_ids = tuple(
            set(
                (
                    await self._session.scalars(
                        select(AttendanceAssignment.employee_id).where(
                            AttendanceAssignment.worksite_id == period.worksite_id,
                            AttendanceAssignment.effective_from <= period_end,
                            or_(
                                AttendanceAssignment.effective_to.is_(None),
                                AttendanceAssignment.effective_to
                                >= period.period_month,
                            ),
                        )
                    )
                ).all()
            )
        )
        if not assigned_employee_ids:
            return ()
        conflicting_employee_id = await self._session.scalar(
            select(AttendanceAssignment.employee_id).where(
                AttendanceAssignment.employee_id.in_(assigned_employee_ids),
                AttendanceAssignment.worksite_id != period.worksite_id,
                AttendanceAssignment.effective_from <= period_end,
                or_(
                    AttendanceAssignment.effective_to.is_(None),
                    AttendanceAssignment.effective_to >= period.period_month,
                ),
            )
        )
        if conflicting_employee_id is not None:
            raise DomainError(
                code="HR_PAYROLL_EMPLOYEE_WORKSITE_AMBIGUOUS",
                message="An employee changes worksite within this payroll month.",
                status_code=409,
            )
        return tuple(
            (
                await self._session.scalars(
                    select(Employee)
                    .where(
                        Employee.id.in_(assigned_employee_ids),
                        Employee.join_date <= period_end,
                    )
                    .order_by(Employee.employee_code)
                )
            ).all()
        )

    async def list_periods(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        worksite_id: UUID | None,
        period_month: date | None,
    ) -> tuple[tuple[PayrollPeriodData, ...], int]:
        self._require_super_admin(principal)
        criteria = []
        if worksite_id is not None:
            criteria.append(PayrollPeriod.worksite_id == worksite_id)
        if period_month is not None:
            criteria.append(PayrollPeriod.period_month == period_month)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(PayrollPeriod).where(*criteria)
            )
            or 0
        )
        periods = tuple(
            (
                await self._session.scalars(
                    select(PayrollPeriod)
                    .where(*criteria)
                    .order_by(
                        PayrollPeriod.period_month.desc(),
                        PayrollPeriod.created_at.desc(),
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._period_data(period) for period in periods), total

    async def create_period(
        self,
        principal: AuthPrincipal,
        payload: CreatePayrollPeriodRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> PayrollPeriodData:
        self._require_super_admin(principal)
        worksite = await self._session.get(AttendanceWorksite, payload.worksite_id)
        if worksite is None:
            raise DomainError(
                code="HR_PAYROLL_WORKSITE_NOT_FOUND",
                message="Payroll worksite was not found.",
                status_code=404,
            )
        existing_id = await self._session.scalar(
            select(PayrollPeriod.id).where(
                PayrollPeriod.worksite_id == payload.worksite_id,
                PayrollPeriod.period_month == payload.period_month,
            )
        )
        if existing_id is not None:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_EXISTS",
                message="A payroll period already exists for this worksite and month.",
                status_code=409,
            )
        period = PayrollPeriod(
            worksite_id=payload.worksite_id,
            period_month=payload.period_month,
            standard_workdays=payload.standard_workdays,
        )
        self._session.add(period)
        await self._session.flush()
        await self._session.refresh(period)
        data = self._period_data(period)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.payroll.created",
            resource_type="payroll_period",
            resource_id=str(period.id),
            after={
                "status": period.status.value,
                "period_month": period.period_month.isoformat(),
                "worksite_id": str(period.worksite_id),
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return data

    async def get_period(
        self, principal: AuthPrincipal, payroll_period_id: UUID
    ) -> PayrollPeriodDetailData:
        self._require_super_admin(principal)
        period = await self._session.get(PayrollPeriod, payroll_period_id)
        if period is None:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_NOT_FOUND",
                message="Payroll period was not found.",
                status_code=404,
            )
        entries = tuple(
            (
                await self._session.scalars(
                    select(PayrollEntry)
                    .where(PayrollEntry.payroll_period_id == period.id)
                    .order_by(PayrollEntry.employee_code)
                )
            ).all()
        )
        return self._period_detail_data(period, entries)

    async def update_entry(
        self,
        principal: AuthPrincipal,
        payroll_period_id: UUID,
        payroll_entry_id: UUID,
        payload: UpdatePayrollEntryRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> PayrollEntryData:
        self._require_super_admin(principal)
        period = await self._session.scalar(
            select(PayrollPeriod)
            .where(PayrollPeriod.id == payroll_period_id)
            .with_for_update()
        )
        if period is None:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_NOT_FOUND",
                message="Payroll period was not found.",
                status_code=404,
            )
        if period.status != PayrollPeriodStatus.DRAFT:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_NOT_DRAFT",
                message="Only draft payroll periods can be adjusted.",
                status_code=409,
            )
        entry = await self._session.scalar(
            select(PayrollEntry)
            .where(
                PayrollEntry.id == payroll_entry_id,
                PayrollEntry.payroll_period_id == period.id,
            )
            .with_for_update()
        )
        if entry is None:
            raise DomainError(
                code="HR_PAYROLL_ENTRY_NOT_FOUND",
                message="Payroll entry was not found in this period.",
                status_code=404,
            )
        changed_fields: list[str] = []
        for field_name in ("allowance", "social_insurance", "income_tax"):
            value = getattr(payload, field_name)
            if value is not None:
                setattr(entry, field_name, round_vnd(value))
                changed_fields.append(field_name)
        period.calculated_at = None
        await self._session.flush()
        await self._session.refresh(entry)
        data = self._entry_data(entry)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.payroll.entry_adjusted",
            resource_type="payroll_entry",
            resource_id=str(entry.id),
            after={"changed_fields": changed_fields},
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return data

    async def recalculate_period_data(
        self,
        principal: AuthPrincipal,
        payroll_period_id: UUID,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> tuple[PayrollEntryData, ...]:
        entries = await self.recalculate_draft_period(
            principal,
            payroll_period_id,
            audit=audit,
            request_id=request_id,
            user_agent=user_agent,
        )
        return tuple(self._entry_data(entry) for entry in entries)

    async def confirm_period(
        self,
        principal: AuthPrincipal,
        payroll_period_id: UUID,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> PayrollPeriodData:
        self._require_super_admin(principal)
        period = await self._session.scalar(
            select(PayrollPeriod)
            .where(PayrollPeriod.id == payroll_period_id)
            .with_for_update()
        )
        if period is None:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_NOT_FOUND",
                message="Payroll period was not found.",
                status_code=404,
            )
        if period.status != PayrollPeriodStatus.DRAFT:
            raise DomainError(
                code="HR_PAYROLL_CONFIRMATION_INVALID",
                message="Only draft payroll periods can be confirmed.",
                status_code=409,
            )
        entry_count = int(
            await self._session.scalar(
                select(func.count())
                .select_from(PayrollEntry)
                .where(PayrollEntry.payroll_period_id == period.id)
            )
            or 0
        )
        if period.calculated_at is None or entry_count == 0:
            raise DomainError(
                code="HR_PAYROLL_CALCULATION_REQUIRED",
                message="Calculate at least one payroll entry before confirmation.",
                status_code=409,
            )
        period.status = PayrollPeriodStatus.CONFIRMED
        period.confirmed_at = self._now()
        period.confirmed_by_user_id = principal.user_id
        await self._session.flush()
        await self._session.refresh(period)
        data = self._period_data(period)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.payroll.confirmed",
            resource_type="payroll_period",
            resource_id=str(period.id),
            after={"status": period.status.value, "entry_count": entry_count},
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return data

    async def mark_period_paid(
        self,
        principal: AuthPrincipal,
        payroll_period_id: UUID,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> PayrollPeriodData:
        self._require_super_admin(principal)
        period = await self._session.scalar(
            select(PayrollPeriod)
            .where(PayrollPeriod.id == payroll_period_id)
            .with_for_update()
        )
        if period is None:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_NOT_FOUND",
                message="Payroll period was not found.",
                status_code=404,
            )
        if period.status != PayrollPeriodStatus.CONFIRMED:
            raise DomainError(
                code="HR_PAYROLL_PAYMENT_INVALID",
                message="Only confirmed payroll periods can be marked paid.",
                status_code=409,
            )
        period.status = PayrollPeriodStatus.PAID
        period.paid_at = self._now()
        period.paid_by_user_id = principal.user_id
        await self._session.flush()
        await self._session.refresh(period)
        data = self._period_data(period)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.payroll.paid",
            resource_type="payroll_period",
            resource_id=str(period.id),
            after={"status": period.status.value},
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return data

    async def recalculate_draft_period(
        self,
        principal: AuthPrincipal,
        payroll_period_id: UUID,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> tuple[PayrollEntry, ...]:
        self._require_super_admin(principal)
        period = await self._session.scalar(
            select(PayrollPeriod)
            .where(PayrollPeriod.id == payroll_period_id)
            .with_for_update()
        )
        if period is None:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_NOT_FOUND",
                message="Payroll period was not found.",
                status_code=404,
            )
        if period.status != PayrollPeriodStatus.DRAFT:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_NOT_DRAFT",
                message="Only draft payroll periods can be recalculated.",
                status_code=409,
            )
        if period.period_month.day != 1:
            raise DomainError(
                code="HR_PAYROLL_PERIOD_MONTH_INVALID",
                message="Payroll period must start on the first day of the month.",
                status_code=422,
            )

        timezone = await self._payroll_timezone(period)
        employees = await self._eligible_employees(period)
        employee_ids = tuple(employee.id for employee in employees)
        existing_entries = tuple(
            (
                await self._session.scalars(
                    select(PayrollEntry)
                    .where(PayrollEntry.payroll_period_id == period.id)
                    .with_for_update()
                )
            ).all()
        )
        entries_by_employee = {entry.employee_id: entry for entry in existing_entries}
        if not set(entries_by_employee).issubset(employee_ids):
            raise DomainError(
                code="HR_PAYROLL_SOURCE_CHANGED",
                message="Payroll source changed after entries were created.",
                status_code=409,
            )

        attendance_by_employee: dict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        overtime_by_employee: dict[UUID, list[OvertimeInterval]] = defaultdict(list)
        if employee_ids:
            attendance_rows = tuple(
                (
                    await self._session.scalars(
                        select(Attendance).where(
                            Attendance.employee_id.in_(employee_ids),
                            Attendance.work_date >= period.period_month,
                            Attendance.work_date
                            <= self._period_end(period.period_month),
                        )
                    )
                ).all()
            )
            for attendance in attendance_rows:
                attendance_by_employee[attendance.employee_id] += (
                    PAYABLE_ATTENDANCE_WEIGHTS.get(attendance.status, Decimal("0"))
                )

            period_start, period_end = local_month_bounds(
                period_month=period.period_month, timezone=timezone
            )
            overtime_rows = tuple(
                (
                    await self._session.scalars(
                        select(OvertimeRequest).where(
                            OvertimeRequest.employee_id.in_(employee_ids),
                            OvertimeRequest.status == OvertimeRequestStatus.APPROVED,
                            OvertimeRequest.start_at < period_end,
                            OvertimeRequest.end_at > period_start,
                        )
                    )
                ).all()
            )
            for overtime in overtime_rows:
                overtime_by_employee[overtime.employee_id].append(
                    OvertimeInterval(
                        start_at=overtime.start_at,
                        end_at=overtime.end_at,
                        status=overtime.status,
                    )
                )

        entries: list[PayrollEntry] = []
        for employee in employees:
            entry = entries_by_employee.get(employee.id)
            allowance = entry.allowance if entry is not None else Decimal("0")
            social_insurance = (
                entry.social_insurance if entry is not None else Decimal("0")
            )
            income_tax = entry.income_tax if entry is not None else Decimal("0")
            workdays = attendance_by_employee[employee.id]
            overtime_hours = approved_overtime_hours_for_local_month(
                tuple(overtime_by_employee[employee.id]),
                period_month=period.period_month,
                timezone=timezone,
            )
            calculation = calculate_payroll(
                PayrollCalculationInput(
                    base_salary=employee.base_salary or Decimal("0"),
                    standard_workdays=period.standard_workdays,
                    attendance_workdays=workdays,
                    approved_overtime_hours=overtime_hours,
                    allowance=allowance,
                    social_insurance=social_insurance,
                    income_tax=income_tax,
                )
            )
            if entry is None:
                entry = PayrollEntry(
                    payroll_period_id=period.id,
                    employee_id=employee.id,
                    employee_code=employee.employee_code,
                    employee_name=employee.full_name,
                    base_salary=round_vnd(employee.base_salary or Decimal("0")),
                )
                self._session.add(entry)
            entry.employee_code = employee.employee_code
            entry.employee_name = employee.full_name
            entry.base_salary = round_vnd(employee.base_salary or Decimal("0"))
            entry.attendance_workdays = workdays
            entry.approved_overtime_hours = overtime_hours
            entry.daily_salary = calculation.daily_salary
            entry.overtime_salary = calculation.overtime_salary
            entry.gross_pay = calculation.gross_pay
            entry.total_deductions = calculation.total_deductions
            entry.net_pay = calculation.net_pay
            entries.append(entry)

        period.calculated_at = self._now()
        await self._session.flush()
        await self._session.refresh(period)
        for entry in entries:
            await self._session.refresh(entry)
        audit.record(
            actor_user_id=principal.user_id,
            action="hr.payroll.calculated",
            resource_type="payroll_period",
            resource_id=str(period.id),
            after={
                "status": period.status.value,
                "period_month": period.period_month.isoformat(),
                "entry_count": len(entries),
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        await self._session.commit()
        return tuple(entries)
