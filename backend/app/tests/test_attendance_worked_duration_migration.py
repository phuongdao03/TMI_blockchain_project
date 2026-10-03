import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_existing_short_and_open_attendance_is_not_credited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "attendance-duration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0095_attendance_work_schedule")
        department_id, employee_id, worksite_id = (
            uuid4().hex,
            uuid4().hex,
            uuid4().hex,
        )
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO departments (id, code, name) "
                "VALUES (?, 'OPS', 'Operations')",
                (department_id,),
            )
            connection.execute(
                "INSERT INTO employees "
                "(id, employee_code, full_name, email, department_id, "
                "position, join_date) "
                "VALUES (?, 'OPS-01', 'Employee', 'employee@example.com', "
                "?, 'Staff', '2026-01-01')",
                (employee_id, department_id),
            )
            connection.execute(
                "INSERT INTO attendance_worksites (id, code, name) "
                "VALUES (?, 'HQ', 'Headquarters')",
                (worksite_id,),
            )
            connection.execute(
                "INSERT INTO payroll_periods "
                "(id, worksite_id, period_month, standard_workdays, "
                "status, calculated_at) "
                "VALUES (?, ?, '2026-10-01', 22, 'DRAFT', "
                "'2026-10-03 10:00:00')",
                (uuid4().hex, worksite_id),
            )
            connection.executemany(
                "INSERT INTO attendance "
                "(id, employee_id, work_date, check_in_at, check_out_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        uuid4().hex,
                        employee_id,
                        "2026-10-01",
                        "2026-10-01 10:06:00",
                        "2026-10-01 10:08:00",
                        "PRESENT",
                    ),
                    (
                        uuid4().hex,
                        employee_id,
                        "2026-10-02",
                        "2026-10-02 01:16:00",
                        None,
                        "LATE",
                    ),
                    (
                        uuid4().hex,
                        employee_id,
                        "2026-10-03",
                        "2026-10-03 01:00:00",
                        "2026-10-03 09:00:00",
                        "PRESENT",
                    ),
                    (
                        uuid4().hex,
                        employee_id,
                        "2026-10-04",
                        "2026-10-04 01:00:00",
                        "2026-10-04 06:00:00",
                        "LATE",
                    ),
                ],
            )

        command.upgrade(config, "0096_attendance_worked_duration")
        with sqlite3.connect(database_path) as connection:
            statuses = dict(
                connection.execute("SELECT work_date, status FROM attendance")
            )
            draft_calculated_at = connection.execute(
                "SELECT calculated_at FROM payroll_periods WHERE status = 'DRAFT'"
            ).fetchone()[0]
            schema = connection.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'attendance'"
            ).fetchone()[0]
        assert statuses == {
            "2026-10-01": "INCOMPLETE",
            "2026-10-02": "IN_PROGRESS",
            "2026-10-03": "PRESENT",
            "2026-10-04": "HALF_DAY",
        }
        assert "'INCOMPLETE'" in schema and "'IN_PROGRESS'" in schema
        assert draft_calculated_at is None

        command.downgrade(config, "0095_attendance_work_schedule")
        with sqlite3.connect(database_path) as connection:
            downgraded = dict(
                connection.execute("SELECT work_date, status FROM attendance")
            )
        assert downgraded["2026-10-01"] == "PENDING"
        assert downgraded["2026-10-02"] == "PENDING"
    finally:
        get_settings.cache_clear()
