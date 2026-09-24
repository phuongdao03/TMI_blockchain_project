from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.modules.hr.models import OvertimeRequestStatus

VND_QUANTUM = Decimal("1")
OVERTIME_MULTIPLIER = Decimal("1.50")
HOURS_PER_WORKDAY = Decimal("8")


@dataclass(frozen=True)
class PayrollCalculationInput:
    base_salary: Decimal
    standard_workdays: int
    attendance_workdays: Decimal
    approved_overtime_hours: Decimal
    allowance: Decimal
    social_insurance: Decimal
    income_tax: Decimal


@dataclass(frozen=True)
class PayrollCalculationResult:
    daily_salary: Decimal
    overtime_salary: Decimal
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal


@dataclass(frozen=True)
class OvertimeInterval:
    start_at: datetime
    end_at: datetime
    status: OvertimeRequestStatus


def round_vnd(value: Decimal) -> Decimal:
    return value.quantize(VND_QUANTUM, rounding=ROUND_HALF_UP)


def _validate(input_data: PayrollCalculationInput) -> None:
    if not 1 <= input_data.standard_workdays <= 31:
        raise ValueError("standard_workdays must be between 1 and 31")
    for field_name, value in (
        ("base_salary", input_data.base_salary),
        ("attendance_workdays", input_data.attendance_workdays),
        ("approved_overtime_hours", input_data.approved_overtime_hours),
        ("allowance", input_data.allowance),
        ("social_insurance", input_data.social_insurance),
        ("income_tax", input_data.income_tax),
    ):
        if value < 0:
            raise ValueError(f"{field_name} must not be negative")


def calculate_payroll(input_data: PayrollCalculationInput) -> PayrollCalculationResult:
    """Calculate one VND payroll snapshot from already-authorized source values."""
    _validate(input_data)

    base_salary = round_vnd(input_data.base_salary)
    allowance = round_vnd(input_data.allowance)
    social_insurance = round_vnd(input_data.social_insurance)
    income_tax = round_vnd(input_data.income_tax)
    daily_salary = round_vnd(base_salary / Decimal(input_data.standard_workdays))
    attendance_pay = round_vnd(daily_salary * input_data.attendance_workdays)
    overtime_salary = round_vnd(
        daily_salary
        / HOURS_PER_WORKDAY
        * input_data.approved_overtime_hours
        * OVERTIME_MULTIPLIER
    )
    gross_pay = round_vnd(attendance_pay + allowance + overtime_salary)
    total_deductions = round_vnd(social_insurance + income_tax)
    net_pay = max(Decimal("0"), gross_pay - total_deductions)

    return PayrollCalculationResult(
        daily_salary=daily_salary,
        overtime_salary=overtime_salary,
        gross_pay=gross_pay,
        total_deductions=total_deductions,
        net_pay=net_pay,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        # Production input is validated as timezone-aware before persistence.
        # SQLite test backends return DateTime(timezone=True) as naive values,
        # so preserve the storage contract and interpret those rows as UTC.
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def local_month_bounds(
    *, period_month: date, timezone: str
) -> tuple[datetime, datetime]:
    if period_month.day != 1:
        raise ValueError("period_month must be the first day of its month")
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ValueError("timezone must be a valid IANA timezone") from error

    if period_month.month == 12:
        next_month = date(period_month.year + 1, 1, 1)
    else:
        next_month = date(period_month.year, period_month.month + 1, 1)
    return (
        datetime(period_month.year, period_month.month, 1, tzinfo=zone).astimezone(UTC),
        datetime(next_month.year, next_month.month, 1, tzinfo=zone).astimezone(UTC),
    )


def _duration_hours(start_at: datetime, end_at: datetime) -> Decimal:
    duration = end_at - start_at
    total_microseconds = (
        (duration.days * 86_400) + duration.seconds
    ) * 1_000_000 + duration.microseconds
    return Decimal(total_microseconds) / Decimal(3_600_000_000)


def approved_overtime_hours_for_local_month(
    intervals: tuple[OvertimeInterval, ...],
    *,
    period_month: date,
    timezone: str,
) -> Decimal:
    """Return approved OT inside one worksite-local calendar month.

    Intervals crossing the local month boundary are clipped before aggregation,
    which avoids a UTC date filter moving OT into the wrong payroll period.
    """
    period_start, period_end = local_month_bounds(
        period_month=period_month, timezone=timezone
    )
    total_hours = Decimal("0")
    for interval in intervals:
        if interval.status != OvertimeRequestStatus.APPROVED:
            continue
        interval_start = _as_utc(interval.start_at)
        interval_end = _as_utc(interval.end_at)
        if interval_end <= interval_start:
            raise ValueError("overtime interval must end after it starts")
        overlap_start = max(interval_start, period_start)
        overlap_end = min(interval_end, period_end)
        if overlap_end > overlap_start:
            total_hours += _duration_hours(overlap_start, overlap_end)
    return total_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
