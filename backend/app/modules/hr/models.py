from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class DepartmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class EmploymentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    TERMINATED = "TERMINATED"


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    LATE = "LATE"
    ABSENT = "ABSENT"
    LEAVE = "LEAVE"
    HALF_DAY = "HALF_DAY"
    OT = "OT"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


class AttendanceWorksiteStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AttendanceLocationEventType(StrEnum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"


class AttendanceLocationOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    OUTSIDE_WORKSITE = "OUTSIDE_WORKSITE"
    LOW_ACCURACY = "LOW_ACCURACY"
    LOCATION_UNAVAILABLE = "LOCATION_UNAVAILABLE"
    EXCEPTION_APPROVED = "EXCEPTION_APPROVED"


class AttendanceLocationExceptionStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LeaveRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OvertimeRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class PayrollPeriodStatus(StrEnum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda values: [value.value for value in values],
        validate_strings=True,
        native_enum=False,
        create_constraint=True,
    )


class Department(UtcTimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DepartmentStatus] = mapped_column(
        _enum(DepartmentStatus, "department_status"),
        nullable=False,
        default=DepartmentStatus.ACTIVE,
        server_default=DepartmentStatus.ACTIVE.value,
    )


class Employee(UtcTimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        Index("uq_employees_user_id", "user_id", unique=True),
        Index("ix_employees_department_id", "department_id"),
        Index("ix_employees_status", "employment_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    employee_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    department_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[str] = mapped_column(String(160), nullable=False)
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        _enum(EmploymentStatus, "employment_status"),
        nullable=False,
        default=EmploymentStatus.ACTIVE,
        server_default=EmploymentStatus.ACTIVE.value,
    )
    join_date: Mapped[date] = mapped_column(Date, nullable=False)
    contract_type: Mapped[str | None] = mapped_column(String(64))
    base_salary: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class AttendanceWorksite(UtcTimestampMixin, Base):
    __tablename__ = "attendance_worksites"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[AttendanceWorksiteStatus] = mapped_column(
        _enum(AttendanceWorksiteStatus, "attendance_worksite_status"),
        nullable=False,
        default=AttendanceWorksiteStatus.ACTIVE,
        server_default=AttendanceWorksiteStatus.ACTIVE.value,
    )


class AttendanceWorksitePolicy(UtcTimestampMixin, Base):
    __tablename__ = "attendance_worksite_policies"
    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="attendance_worksite_policy_effective_range",
        ),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="attendance_worksite_policy_latitude",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="attendance_worksite_policy_longitude",
        ),
        CheckConstraint(
            "radius_meters > 0",
            name="attendance_worksite_policy_radius_positive",
        ),
        CheckConstraint(
            "max_accuracy_meters > 0",
            name="attendance_worksite_policy_accuracy_positive",
        ),
        UniqueConstraint("worksite_id", "effective_from"),
        Index(
            "ix_attendance_worksite_policies_worksite_effective",
            "worksite_id",
            "effective_from",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    worksite_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("attendance_worksites.id", ondelete="RESTRICT"), nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    radius_meters: Mapped[int] = mapped_column(nullable=False)
    max_accuracy_meters: Mapped[int] = mapped_column(nullable=False)


class AttendanceAssignment(UtcTimestampMixin, Base):
    __tablename__ = "attendance_assignments"
    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="attendance_assignment_effective_range",
        ),
        UniqueConstraint("employee_id", "effective_from"),
        Index(
            "ix_attendance_assignments_employee_effective",
            "employee_id",
            "effective_from",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    worksite_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("attendance_worksites.id", ondelete="RESTRICT"), nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    schedule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    holiday_calendar_code: Mapped[str] = mapped_column(String(64), nullable=False)


class Attendance(UtcTimestampMixin, Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("employee_id", "work_date"),
        Index("ix_attendance_work_date", "work_date"),
        Index("ix_attendance_employee_work_date", "employee_id", "work_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_in_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    check_in_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    check_out_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    check_out_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    status: Mapped[AttendanceStatus] = mapped_column(
        _enum(AttendanceStatus, "attendance_status"),
        nullable=False,
        default=AttendanceStatus.PRESENT,
        server_default=AttendanceStatus.PRESENT.value,
    )
    late_minutes: Mapped[int] = mapped_column(default=0, server_default="0")
    early_leave_minutes: Mapped[int] = mapped_column(default=0, server_default="0")
    note: Mapped[str | None] = mapped_column(Text)


class AttendanceLocationEvidence(UtcTimestampMixin, Base):
    __tablename__ = "attendance_location_evidence"
    __table_args__ = (
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="location_evidence_latitude",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="location_evidence_longitude",
        ),
        CheckConstraint(
            "accuracy_meters > 0",
            name="location_evidence_accuracy_positive",
        ),
        CheckConstraint(
            "distance_meters >= 0",
            name="location_evidence_distance_nonnegative",
        ),
        CheckConstraint(
            "permitted_radius_meters > 0",
            name="location_evidence_radius_positive",
        ),
        CheckConstraint(
            "max_accuracy_meters > 0",
            name="location_evidence_max_accuracy_positive",
        ),
        Index(
            "uq_attendance_location_evidence_attendance_event",
            "attendance_id",
            "event_type",
            unique=True,
        ),
        Index("ix_attendance_location_evidence_retention_until", "retention_until"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    attendance_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("attendance.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[AttendanceLocationEventType] = mapped_column(
        _enum(AttendanceLocationEventType, "location_evidence_event_type"),
        nullable=False,
    )
    worksite_policy_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("attendance_worksite_policies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    client_captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    accuracy_meters: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    distance_meters: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    effective_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    permitted_radius_meters: Mapped[int] = mapped_column(nullable=False)
    max_accuracy_meters: Mapped[int] = mapped_column(nullable=False)
    outcome: Mapped[AttendanceLocationOutcome] = mapped_column(
        _enum(AttendanceLocationOutcome, "location_evidence_outcome"),
        nullable=False,
    )
    retention_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    location_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AttendanceLocationException(UtcTimestampMixin, Base):
    __tablename__ = "attendance_location_exceptions"
    __table_args__ = (
        Index(
            "uq_attendance_location_exceptions_evidence",
            "location_evidence_id",
            unique=True,
        ),
        Index(
            "ix_attendance_location_exceptions_status_created",
            "status",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    attendance_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("attendance.id", ondelete="RESTRICT"), nullable=False
    )
    location_evidence_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("attendance_location_evidence.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[AttendanceLocationExceptionStatus] = mapped_column(
        _enum(AttendanceLocationExceptionStatus, "location_exception_status"),
        nullable=False,
        default=AttendanceLocationExceptionStatus.PENDING,
        server_default=AttendanceLocationExceptionStatus.PENDING.value,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decision_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeaveRequest(UtcTimestampMixin, Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        Index(
            "ix_leave_requests_employee_status_created",
            "employee_id",
            "status",
            "created_at",
        ),
        Index("ix_leave_requests_status_start_date", "status", "start_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    leave_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LeaveRequestStatus] = mapped_column(
        _enum(LeaveRequestStatus, "leave_request_status"),
        nullable=False,
        default=LeaveRequestStatus.PENDING,
        server_default=LeaveRequestStatus.PENDING.value,
    )
    decision_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OvertimeRequest(UtcTimestampMixin, Base):
    __tablename__ = "overtime_requests"
    __table_args__ = (
        Index(
            "ix_overtime_requests_employee_status_created",
            "employee_id",
            "status",
            "created_at",
        ),
        Index("ix_overtime_requests_status_start_at", "status", "start_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OvertimeRequestStatus] = mapped_column(
        _enum(OvertimeRequestStatus, "overtime_request_status"),
        nullable=False,
        default=OvertimeRequestStatus.PENDING,
        server_default=OvertimeRequestStatus.PENDING.value,
    )
    decision_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PayrollPeriod(UtcTimestampMixin, Base):
    __tablename__ = "payroll_periods"
    __table_args__ = (
        CheckConstraint(
            "standard_workdays >= 1 AND standard_workdays <= 31",
            name="payroll_period_standard_workdays_range",
        ),
        CheckConstraint("currency = 'VND'", name="payroll_period_currency_vnd"),
        UniqueConstraint(
            "worksite_id", "period_month", name="uq_payroll_periods_worksite_month"
        ),
        Index("ix_payroll_periods_status_month", "status", "period_month"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    worksite_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("attendance_worksites.id", ondelete="RESTRICT"), nullable=False
    )
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="VND", server_default="VND"
    )
    standard_workdays: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[PayrollPeriodStatus] = mapped_column(
        _enum(PayrollPeriodStatus, "payroll_period_status"),
        nullable=False,
        default=PayrollPeriodStatus.DRAFT,
        server_default=PayrollPeriodStatus.DRAFT.value,
    )
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class PayrollEntry(UtcTimestampMixin, Base):
    __tablename__ = "payroll_entries"
    __table_args__ = (
        CheckConstraint(
            "base_salary >= 0", name="payroll_entry_base_salary_nonnegative"
        ),
        CheckConstraint(
            "attendance_workdays >= 0", name="payroll_entry_workdays_nonnegative"
        ),
        CheckConstraint(
            "approved_overtime_hours >= 0", name="payroll_entry_overtime_nonnegative"
        ),
        CheckConstraint("allowance >= 0", name="payroll_entry_allowance_nonnegative"),
        CheckConstraint(
            "social_insurance >= 0", name="payroll_entry_social_insurance_nonnegative"
        ),
        CheckConstraint("income_tax >= 0", name="payroll_entry_income_tax_nonnegative"),
        CheckConstraint(
            "daily_salary >= 0", name="payroll_entry_daily_salary_nonnegative"
        ),
        CheckConstraint(
            "overtime_salary >= 0", name="payroll_entry_overtime_salary_nonnegative"
        ),
        CheckConstraint("gross_pay >= 0", name="payroll_entry_gross_pay_nonnegative"),
        CheckConstraint(
            "total_deductions >= 0", name="payroll_entry_total_deductions_nonnegative"
        ),
        CheckConstraint("net_pay >= 0", name="payroll_entry_net_pay_nonnegative"),
        UniqueConstraint(
            "payroll_period_id",
            "employee_id",
            name="uq_payroll_entries_period_employee",
        ),
        Index("ix_payroll_entries_employee_period", "employee_id", "payroll_period_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    payroll_period_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("payroll_periods.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    employee_code: Mapped[str] = mapped_column(String(32), nullable=False)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    attendance_workdays: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    approved_overtime_hours: Mapped[Decimal] = mapped_column(
        Numeric(7, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    allowance: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
    social_insurance: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
    income_tax: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
    daily_salary: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
    overtime_salary: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
    gross_pay: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
    net_pay: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal("0"), server_default="0"
    )
