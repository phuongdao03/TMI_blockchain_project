from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.modules.hr.models import (
    AttendanceLocationEventType,
    AttendanceLocationExceptionStatus,
    AttendanceLocationOutcome,
    AttendanceStatus,
    AttendanceWorksiteStatus,
    DepartmentStatus,
    EmploymentStatus,
    LeaveRequestStatus,
    OvertimeRequestStatus,
    PayrollPeriodStatus,
)


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class HrSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="forbid",
    )


class CreateDepartmentRequest(HrSchema):
    code: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$")]
    name: Annotated[str, Field(min_length=2, max_length=160)]
    description: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("code", "name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()


class UpdateDepartmentRequest(HrSchema):
    name: Annotated[str, Field(min_length=2, max_length=160)]
    description: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class DepartmentData(HrSchema):
    id: UUID
    code: str
    name: str
    description: str | None
    status: DepartmentStatus
    created_at: datetime
    updated_at: datetime


class CreateEmployeeRequest(HrSchema):
    employee_code: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$")]
    user_id: UUID | None = None
    full_name: Annotated[str, Field(min_length=2, max_length=255)]
    email: EmailStr
    phone: Annotated[str | None, Field(max_length=32)] = None
    department_id: UUID
    position: Annotated[str, Field(min_length=2, max_length=160)]
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    join_date: date
    contract_type: Annotated[str | None, Field(max_length=64)] = None
    base_salary: Annotated[Decimal | None, Field(ge=0, decimal_places=2)] = None

    @field_validator("employee_code", "full_name", "position")
    @classmethod
    def strip_employee_fields(cls, value: str) -> str:
        return value.strip()


class UpdateEmployeeRequest(HrSchema):
    user_id: UUID | None = None
    full_name: Annotated[str | None, Field(min_length=2, max_length=255)] = None
    email: EmailStr | None = None
    phone: Annotated[str | None, Field(max_length=32)] = None
    department_id: UUID | None = None
    position: Annotated[str | None, Field(min_length=2, max_length=160)] = None
    employment_status: EmploymentStatus | None = None
    contract_type: Annotated[str | None, Field(max_length=64)] = None
    base_salary: Annotated[Decimal | None, Field(ge=0, decimal_places=2)] = None


class EmployeeData(HrSchema):
    id: UUID
    employee_code: str
    user_id: UUID | None
    full_name: str
    email: EmailStr
    phone: str | None
    department_id: UUID
    department_name: str
    position: str
    employment_status: EmploymentStatus
    join_date: date
    contract_type: str | None
    base_salary: Decimal | None
    created_at: datetime
    updated_at: datetime


class LocationCaptureRequest(HrSchema):
    """One foreground browser location sample, never a client geofence decision."""

    latitude: Annotated[Decimal, Field(ge=-90, le=90, decimal_places=6)]
    longitude: Annotated[Decimal, Field(ge=-180, le=180, decimal_places=6)]
    accuracy_meters: Annotated[Decimal, Field(gt=0, le=20_037_509, decimal_places=2)]
    client_captured_at: datetime

    @field_validator("client_captured_at")
    @classmethod
    def require_timezone_aware_capture_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Client capture time must include a timezone offset.")
        return value


class CheckInRequest(LocationCaptureRequest):
    note: Annotated[str | None, Field(max_length=2000)] = None


class CheckOutRequest(LocationCaptureRequest):
    pass


class AttendanceData(HrSchema):
    id: UUID
    employee_id: UUID
    employee_name: str
    work_date: date
    check_in_at: datetime | None
    check_out_at: datetime | None
    status: AttendanceStatus
    late_minutes: int
    early_leave_minutes: int
    note: str | None
    created_at: datetime
    updated_at: datetime


class AttendanceWorkdayContextData(HrSchema):
    """Server-derived local workday metadata without location evidence."""

    work_date: date | None
    timezone: str | None

    @model_validator(mode="after")
    def require_complete_context(self) -> "AttendanceWorkdayContextData":
        if (self.work_date is None) != (self.timezone is None):
            raise ValueError("Workday context must include both date and timezone.")
        return self


class AdminAttendanceData(AttendanceData):
    employee_code: str
    department_name: str


class CreateAttendanceWorksiteRequest(HrSchema):
    code: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$")]
    name: Annotated[str, Field(min_length=2, max_length=160)]

    @field_validator("code", "name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()


class UpdateAttendanceWorksiteRequest(HrSchema):
    name: Annotated[str | None, Field(min_length=2, max_length=160)] = None
    status: AttendanceWorksiteStatus | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "UpdateAttendanceWorksiteRequest":
        if self.name is None and self.status is None:
            raise ValueError("Provide at least one worksite field to update.")
        return self


class AttendanceWorksiteData(HrSchema):
    id: UUID
    code: str
    name: str
    status: AttendanceWorksiteStatus
    created_at: datetime
    updated_at: datetime


class EffectiveDatedAttendanceRequest(HrSchema):
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_effective_date_range(self) -> "EffectiveDatedAttendanceRequest":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("Effective end date must not be before the start date.")
        return self


class CreateAttendanceWorksitePolicyRequest(EffectiveDatedAttendanceRequest):
    timezone: Annotated[str, Field(min_length=1, max_length=64)]
    latitude: Annotated[Decimal, Field(ge=-90, le=90, max_digits=8, decimal_places=6)]
    longitude: Annotated[
        Decimal, Field(ge=-180, le=180, max_digits=9, decimal_places=6)
    ]
    radius_meters: Annotated[int, Field(gt=0, le=20_037_509)]
    max_accuracy_meters: Annotated[int, Field(gt=0, le=20_037_509)]

    @field_validator("timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            return ZoneInfo(value.strip()).key
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("Timezone must be a valid IANA timezone.") from error


class AttendanceWorksitePolicyData(HrSchema):
    id: UUID
    worksite_id: UUID
    effective_from: date
    effective_to: date | None
    timezone: str
    latitude: Decimal
    longitude: Decimal
    radius_meters: int
    max_accuracy_meters: int
    created_at: datetime
    updated_at: datetime


class CreateAttendanceAssignmentRequest(EffectiveDatedAttendanceRequest):
    employee_id: UUID
    worksite_id: UUID
    schedule_code: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")]
    holiday_calendar_code: Annotated[
        str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    ]


class AttendanceAssignmentData(HrSchema):
    id: UUID
    employee_id: UUID
    employee_code: str
    employee_name: str
    worksite_id: UUID
    worksite_code: str
    worksite_name: str
    effective_from: date
    effective_to: date | None
    schedule_code: str
    holiday_calendar_code: str
    created_at: datetime
    updated_at: datetime


class AttendanceLocationExceptionDecisionRequest(HrSchema):
    status: AttendanceLocationExceptionStatus
    decision_note: Annotated[str, Field(min_length=2, max_length=2000)]

    @field_validator("decision_note")
    @classmethod
    def require_decision_note(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Decision note must not be blank.")
        return stripped

    @model_validator(mode="after")
    def require_final_decision(self) -> "AttendanceLocationExceptionDecisionRequest":
        if self.status == AttendanceLocationExceptionStatus.PENDING:
            raise ValueError("A pending exception cannot be decided as pending.")
        return self


class AttendanceLocationExceptionData(HrSchema):
    id: UUID
    attendance_id: UUID
    location_evidence_id: UUID
    status: AttendanceLocationExceptionStatus
    requested_by_user_id: UUID
    decision_note: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AttendanceLocationEvidenceReviewData(HrSchema):
    id: UUID
    event_type: AttendanceLocationEventType
    worksite_policy_id: UUID
    worksite_code: str
    worksite_name: str
    client_captured_at: datetime
    received_at: datetime
    latitude: Decimal | None
    longitude: Decimal | None
    accuracy_meters: Decimal
    distance_meters: Decimal
    effective_timezone: str
    permitted_radius_meters: int
    max_accuracy_meters: int
    outcome: AttendanceLocationOutcome


class AdminAttendanceLocationExceptionData(AttendanceLocationExceptionData):
    employee_id: UUID
    employee_code: str
    employee_name: str
    work_date: date
    attendance_status: AttendanceStatus
    evidence: AttendanceLocationEvidenceReviewData


class UpdateAttendanceRequest(HrSchema):
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    status: AttendanceStatus | None = None
    late_minutes: Annotated[int | None, Field(ge=0, le=1440)] = None
    early_leave_minutes: Annotated[int | None, Field(ge=0, le=1440)] = None
    note: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("check_in_at", "check_out_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Datetime values must include a timezone offset.")
        return value


class CreateLeaveRequest(HrSchema):
    leave_type: Annotated[str, Field(min_length=2, max_length=64)]
    start_date: date
    end_date: date
    reason: Annotated[str, Field(min_length=2, max_length=2000)]

    @field_validator("leave_type", "reason")
    @classmethod
    def strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("This field must not be blank.")
        return stripped

    @model_validator(mode="after")
    def validate_date_range(self) -> "CreateLeaveRequest":
        if self.end_date < self.start_date:
            raise ValueError("End date must not be before start date.")
        return self


class LeaveDecisionRequest(HrSchema):
    decision_note: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("decision_note")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class LeaveRequestData(HrSchema):
    id: UUID
    employee_id: UUID
    employee_name: str
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: LeaveRequestStatus
    decision_note: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminLeaveRequestData(LeaveRequestData):
    employee_code: str
    department_name: str


class CreateOvertimeRequest(HrSchema):
    start_at: datetime
    end_at: datetime
    reason: Annotated[str, Field(min_length=2, max_length=2000)]

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("Datetime values must include a timezone offset.")
        return value

    @field_validator("reason")
    @classmethod
    def strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("This field must not be blank.")
        return stripped

    @model_validator(mode="after")
    def validate_time_range(self) -> "CreateOvertimeRequest":
        if self.end_at <= self.start_at:
            raise ValueError("End time must be after start time.")
        return self


class OvertimeDecisionRequest(HrSchema):
    decision_note: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("decision_note")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class OvertimeRequestData(HrSchema):
    id: UUID
    employee_id: UUID
    employee_name: str
    start_at: datetime
    end_at: datetime
    reason: str
    status: OvertimeRequestStatus
    decision_note: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminOvertimeRequestData(OvertimeRequestData):
    employee_code: str
    department_name: str


class CreatePayrollPeriodRequest(HrSchema):
    worksite_id: UUID
    period_month: date
    standard_workdays: Annotated[int, Field(ge=1, le=31)]

    @field_validator("period_month")
    @classmethod
    def require_first_day_of_month(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("Payroll period must start on the first day of a month.")
        return value


class UpdatePayrollEntryRequest(HrSchema):
    allowance: Annotated[Decimal | None, Field(ge=0, decimal_places=0)] = None
    social_insurance: Annotated[Decimal | None, Field(ge=0, decimal_places=0)] = None
    income_tax: Annotated[Decimal | None, Field(ge=0, decimal_places=0)] = None

    @model_validator(mode="after")
    def require_adjustment(self) -> "UpdatePayrollEntryRequest":
        if not self.model_fields_set:
            raise ValueError("At least one payroll adjustment is required.")
        return self


class PayrollEntryData(HrSchema):
    id: UUID
    payroll_period_id: UUID
    employee_id: UUID
    employee_code: str
    employee_name: str
    base_salary: Decimal
    attendance_workdays: Decimal
    approved_overtime_hours: Decimal
    allowance: Decimal
    social_insurance: Decimal
    income_tax: Decimal
    daily_salary: Decimal
    overtime_salary: Decimal
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    created_at: datetime
    updated_at: datetime


class PayrollPeriodData(HrSchema):
    id: UUID
    worksite_id: UUID
    period_month: date
    currency: str
    standard_workdays: int
    status: PayrollPeriodStatus
    calculated_at: datetime | None
    confirmed_at: datetime | None
    confirmed_by_user_id: UUID | None
    paid_at: datetime | None
    paid_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class PayrollPeriodDetailData(PayrollPeriodData):
    entries: tuple[PayrollEntryData, ...]


class HrDashboardSummaryData(HrSchema):
    active_employee_count: int
    attendance_pending_count: int
    location_exception_pending_count: int
    leave_pending_count: int
    overtime_pending_count: int
    payroll_draft_count: int
    updated_at: datetime


class ModeratorHrDashboardSummaryData(HrSchema):
    profile_linked: bool
    work_date: date | None
    timezone: str | None
    attendance_status: AttendanceStatus | None
    check_in_at: datetime | None
    check_out_at: datetime | None
    leave_pending_count: int
    overtime_pending_count: int
    updated_at: datetime
