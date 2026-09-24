import asyncio
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User
from app.modules.hr.models import (
    AttendanceWorksite,
    Department,
    Employee,
    PayrollEntry,
    PayrollPeriod,
    PayrollPeriodStatus,
)


async def _create_payroll_tables(engine: object) -> None:
    async with engine.begin() as connection:  # type: ignore[union-attr]
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[
                    User.__table__,
                    Department.__table__,
                    Employee.__table__,
                    AttendanceWorksite.__table__,
                    PayrollPeriod.__table__,
                    PayrollEntry.__table__,
                ],
            )
        )


def test_payroll_period_is_unique_per_worksite_month_and_defaults_to_vnd_draft() -> (
    None
):
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_payroll_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        worksite_id = None
        async with sessions.begin() as session:
            worksite = AttendanceWorksite(
                code="SGN-HQ", name="Văn phòng TP. Hồ Chí Minh"
            )
            session.add(worksite)
            await session.flush()
            worksite_id = worksite.id
            period = PayrollPeriod(
                worksite_id=worksite.id,
                period_month=date(2026, 9, 1),
                standard_workdays=22,
            )
            session.add(period)
            await session.flush()
            assert period.currency == "VND"
            assert period.status == PayrollPeriodStatus.DRAFT

        async with sessions() as session:
            period = await session.scalar(select(PayrollPeriod))
            assert period is not None

        async with sessions() as session:
            assert worksite_id is not None
            session.add(
                PayrollPeriod(
                    worksite_id=worksite_id,
                    period_month=date(2026, 9, 1),
                    standard_workdays=22,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
        await engine.dispose()

    asyncio.run(exercise())


def test_payroll_entry_rejects_negative_monetary_snapshots() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_payroll_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions.begin() as session:
            worksite = AttendanceWorksite(code="SIN-HQ", name="Singapore office")
            department = Department(code="OPS", name="Operations")
            session.add(department)
            session.add(worksite)
            await session.flush()
            employee = Employee(
                employee_code="NV-001",
                full_name="Nguyễn Minh An",
                email="an@example.com",
                department_id=department.id,
                position="Operations specialist",
                join_date=date(2026, 1, 1),
            )
            session.add(employee)
            await session.flush()
            period = PayrollPeriod(
                worksite_id=worksite.id,
                period_month=date(2026, 9, 1),
                standard_workdays=22,
                status=PayrollPeriodStatus.DRAFT,
            )
            session.add(period)
            await session.flush()
            session.add(
                PayrollEntry(
                    payroll_period_id=period.id,
                    employee_id=employee.id,
                    employee_code="NV-001",
                    employee_name="Nguyễn Minh An",
                    base_salary=Decimal("-1"),
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()
        await engine.dispose()

    asyncio.run(exercise())
