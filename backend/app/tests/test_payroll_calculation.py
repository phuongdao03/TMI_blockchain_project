from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.modules.hr.models import OvertimeRequestStatus
from app.modules.hr.payroll import (
    OvertimeInterval,
    PayrollCalculationInput,
    approved_overtime_hours_for_local_month,
    calculate_payroll,
)


def test_calculates_vnd_payroll_with_approved_overtime_rate() -> None:
    result = calculate_payroll(
        PayrollCalculationInput(
            base_salary=Decimal("18000000"),
            standard_workdays=22,
            attendance_workdays=Decimal("20.5"),
            approved_overtime_hours=Decimal("8"),
            allowance=Decimal("2000000"),
            social_insurance=Decimal("1890000"),
            income_tax=Decimal("700000"),
        )
    )

    assert result.daily_salary == Decimal("818182")
    assert result.overtime_salary == Decimal("1227273")
    assert result.gross_pay == Decimal("20000004")
    assert result.total_deductions == Decimal("2590000")
    assert result.net_pay == Decimal("17410004")


def test_caps_net_pay_at_zero_after_deductions() -> None:
    result = calculate_payroll(
        PayrollCalculationInput(
            base_salary=Decimal("10000000"),
            standard_workdays=20,
            attendance_workdays=Decimal("1"),
            approved_overtime_hours=Decimal("0"),
            allowance=Decimal("0"),
            social_insurance=Decimal("600000"),
            income_tax=Decimal("0"),
        )
    )

    assert result.gross_pay == Decimal("500000")
    assert result.net_pay == Decimal("0")


def test_only_counts_approved_overtime_within_worksite_local_month() -> None:
    hours = approved_overtime_hours_for_local_month(
        (
            OvertimeInterval(
                start_at=datetime(2026, 9, 30, 15, tzinfo=UTC),
                end_at=datetime(2026, 9, 30, 19, tzinfo=UTC),
                status=OvertimeRequestStatus.APPROVED,
            ),
            OvertimeInterval(
                start_at=datetime(2026, 9, 15, 10, tzinfo=UTC),
                end_at=datetime(2026, 9, 15, 12, tzinfo=UTC),
                status=OvertimeRequestStatus.PENDING,
            ),
        ),
        period_month=date(2026, 9, 1),
        timezone="Asia/Ho_Chi_Minh",
    )

    assert hours == Decimal("2.00")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("standard_workdays", 0),
        ("attendance_workdays", Decimal("-0.5")),
        ("approved_overtime_hours", Decimal("-1")),
        ("allowance", Decimal("-1")),
    ],
)
def test_rejects_invalid_payroll_inputs(field: str, value: Decimal | int) -> None:
    values: dict[str, Decimal | int] = {
        "base_salary": Decimal("10000000"),
        "standard_workdays": 20,
        "attendance_workdays": Decimal("20"),
        "approved_overtime_hours": Decimal("0"),
        "allowance": Decimal("0"),
        "social_insurance": Decimal("0"),
        "income_tax": Decimal("0"),
    }
    values[field] = value

    with pytest.raises(ValueError):
        calculate_payroll(PayrollCalculationInput(**values))  # type: ignore[arg-type]
