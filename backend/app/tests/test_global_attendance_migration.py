import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
GLOBAL_ATTENDANCE_ADMIN_PERMISSION_CODES = {
    "hr.attendance.worksites.read",
    "hr.attendance.worksites.manage",
}


def test_global_attendance_location_schema_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "global-attendance.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0091_location_retention")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            policy_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list('attendance_worksite_policies')"
                )
            }
            assignment_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list('attendance_assignments')"
                )
            }
            evidence_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list('attendance_location_evidence')"
                )
            }
            exception_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list('attendance_location_exceptions')"
                )
            }
            evidence_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' "
                "AND name = 'attendance_location_evidence'"
            ).fetchone()[0]
            attendance_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' "
                "AND name = 'attendance'"
            ).fetchone()[0]
            exception_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' "
                "AND name = 'attendance_location_exceptions'"
            ).fetchone()[0]
            admin_permission_codes = {
                row[0]
                for row in connection.execute(
                    "SELECT code FROM permissions WHERE code IN (?, ?)",
                    tuple(GLOBAL_ATTENDANCE_ADMIN_PERMISSION_CODES),
                )
            }
        assert {
            "attendance_worksites",
            "attendance_worksite_policies",
            "attendance_assignments",
            "attendance_location_evidence",
            "attendance_location_exceptions",
        }.issubset(tables)
        assert "ix_attendance_worksite_policies_worksite_effective" in policy_indexes
        assert "ix_attendance_assignments_employee_effective" in assignment_indexes
        assert "uq_attendance_location_evidence_attendance_event" in evidence_indexes
        assert "ix_attendance_location_evidence_retention_until" in evidence_indexes
        assert "uq_attendance_location_exceptions_evidence" in exception_indexes
        assert "ix_attendance_location_exceptions_status_created" in exception_indexes
        assert "location_evidence_event_type" in evidence_schema
        assert "location_evidence_outcome" in evidence_schema
        assert "location_evidence_accuracy_positive" in evidence_schema
        assert "retention_until" in evidence_schema
        assert "location_purged_at" in evidence_schema
        assert "'PENDING'" in attendance_schema
        assert "'REJECTED'" in attendance_schema
        assert "location_exception_status" in exception_schema
        assert admin_permission_codes == GLOBAL_ATTENDANCE_ADMIN_PERMISSION_CODES

        command.downgrade(config, "0089_global_attendance_admin")
        with sqlite3.connect(database_path) as connection:
            downgraded_exception_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "attendance_location_exceptions" not in downgraded_exception_tables

        command.downgrade(config, "0088_global_attendance")
        with sqlite3.connect(database_path) as connection:
            downgraded_permission_codes = {
                row[0]
                for row in connection.execute(
                    "SELECT code FROM permissions WHERE code IN (?, ?)",
                    tuple(GLOBAL_ATTENDANCE_ADMIN_PERMISSION_CODES),
                )
            }
        assert not downgraded_permission_codes

        command.downgrade(config, "0087_review_assistance")
        with sqlite3.connect(database_path) as connection:
            downgraded_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "attendance_worksites" not in downgraded_tables
        assert "attendance_worksite_policies" not in downgraded_tables
        assert "attendance_assignments" not in downgraded_tables
        assert "attendance_location_evidence" not in downgraded_tables
    finally:
        get_settings.cache_clear()
