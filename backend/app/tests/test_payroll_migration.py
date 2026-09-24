import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_payroll_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "payroll-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0094_payroll_foundation")
    with sqlite3.connect(database_path) as connection:
        assert _columns(connection, "payroll_periods") == {
            "id",
            "worksite_id",
            "period_month",
            "currency",
            "standard_workdays",
            "status",
            "calculated_at",
            "confirmed_at",
            "confirmed_by_user_id",
            "paid_at",
            "paid_by_user_id",
            "created_at",
            "updated_at",
        }
        assert _columns(connection, "payroll_entries") == {
            "id",
            "payroll_period_id",
            "employee_id",
            "employee_code",
            "employee_name",
            "base_salary",
            "attendance_workdays",
            "approved_overtime_hours",
            "allowance",
            "social_insurance",
            "income_tax",
            "daily_salary",
            "overtime_salary",
            "gross_pay",
            "total_deductions",
            "net_pay",
            "created_at",
            "updated_at",
        }
        permissions = {
            row[0]
            for row in connection.execute(
                "SELECT code FROM permissions WHERE code LIKE 'hr.payroll.%'"
            )
        }
        assert permissions == {"hr.payroll.read", "hr.payroll.manage"}

    command.downgrade(config, "0093_allocation_review")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {"payroll_periods", "payroll_entries"}.isdisjoint(tables)
    get_settings.cache_clear()
