import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
HR_PERMISSION_CODES = {
    "hr.departments.manage",
    "hr.employees.read",
    "hr.employees.manage",
    "hr.attendance.self",
    "hr.leave.self",
    "hr.overtime.self",
}
ATTENDANCE_PERMISSION_CODES = {
    "hr.attendance.read",
    "hr.attendance.adjust",
}
LEAVE_PERMISSION_CODES = {
    "hr.leave.read",
    "hr.leave.manage",
}
OVERTIME_PERMISSION_CODES = {
    "hr.overtime.read",
    "hr.overtime.manage",
}
TASK_PERMISSION_CODES = {
    "work.tasks.read",
    "work.tasks.manage",
}


def test_hr_foundation_schema_and_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "hr-foundation.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0086_task_foundation")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            employee_indexes = {
                row[1] for row in connection.execute("PRAGMA index_list('employees')")
            }
            attendance_indexes = {
                row[1] for row in connection.execute("PRAGMA index_list('attendance')")
            }
            leave_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list('leave_requests')")
            }
            overtime_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list('overtime_requests')")
            }
            task_indexes = {
                row[1] for row in connection.execute("PRAGMA index_list('tasks')")
            }
            task_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'tasks'"
            ).fetchone()[0]
            codes = {
                row[0]
                for row in connection.execute(
                    "SELECT code FROM permissions WHERE code IN ("
                    + ",".join(
                        "?"
                        for _ in (
                            HR_PERMISSION_CODES
                            | ATTENDANCE_PERMISSION_CODES
                            | LEAVE_PERMISSION_CODES
                            | OVERTIME_PERMISSION_CODES
                            | TASK_PERMISSION_CODES
                        )
                    )
                    + ")",
                    tuple(
                        HR_PERMISSION_CODES
                        | ATTENDANCE_PERMISSION_CODES
                        | LEAVE_PERMISSION_CODES
                        | OVERTIME_PERMISSION_CODES
                        | TASK_PERMISSION_CODES
                    ),
                )
            }
        assert {
            "departments",
            "employees",
            "attendance",
            "leave_requests",
            "overtime_requests",
            "tasks",
            "task_checklist_items",
            "task_comments",
            "task_attachments",
            "task_activities",
        }.issubset(tables)
        assert "uq_employees_user_id" in employee_indexes
        assert "ix_attendance_employee_work_date" in attendance_indexes
        assert "ix_leave_requests_employee_status_created" in leave_indexes
        assert "ix_overtime_requests_employee_status_created" in overtime_indexes
        assert "ix_tasks_assignee_status_due" in task_indexes
        assert "task_status" in task_schema
        assert "task_priority" in task_schema
        assert codes == (
            HR_PERMISSION_CODES
            | ATTENDANCE_PERMISSION_CODES
            | LEAVE_PERMISSION_CODES
            | OVERTIME_PERMISSION_CODES
            | TASK_PERMISSION_CODES
        )
        command.downgrade(config, "0085_overtime_foundation")
        with sqlite3.connect(database_path) as connection:
            tables_after_task_downgrade = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            task_codes = {
                row[0]
                for row in connection.execute(
                    "SELECT code FROM permissions WHERE code IN (?, ?)",
                    tuple(TASK_PERMISSION_CODES),
                )
            }
        assert "tasks" not in tables_after_task_downgrade
        assert "task_checklist_items" not in tables_after_task_downgrade
        assert "task_comments" not in tables_after_task_downgrade
        assert "task_attachments" not in tables_after_task_downgrade
        assert "task_activities" not in tables_after_task_downgrade
        assert not task_codes
        command.downgrade(config, "0083_attendance_foundation")
        with sqlite3.connect(database_path) as connection:
            downgraded_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            leave_codes = {
                row[0]
                for row in connection.execute(
                    "SELECT code FROM permissions WHERE code IN (?, ?)",
                    tuple(LEAVE_PERMISSION_CODES),
                )
            }
        assert "leave_requests" not in downgraded_tables
        assert not leave_codes
    finally:
        get_settings.cache_clear()
