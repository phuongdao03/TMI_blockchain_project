from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.hr.schemas import (
    CreatePayrollPeriodRequest,
    UpdatePayrollEntryRequest,
)


def test_payroll_period_request_requires_first_day_of_month() -> None:
    with pytest.raises(ValidationError):
        CreatePayrollPeriodRequest(
            worksite_id=uuid4(),
            period_month=date(2026, 9, 2),
            standard_workdays=22,
        )


def test_payroll_entry_adjustment_requires_an_integer_vnd_change() -> None:
    with pytest.raises(ValidationError):
        UpdatePayrollEntryRequest(allowance=Decimal("1000.50"))

    with pytest.raises(ValidationError):
        UpdatePayrollEntryRequest()

    request = UpdatePayrollEntryRequest(
        allowance=Decimal("2000000"),
        social_insurance=Decimal("1890000"),
    )
    assert request.allowance == Decimal("2000000")
