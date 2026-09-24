import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_review_assistance_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "review-assistance.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0087_review_assistance")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(review_assistance_requests)"
                )
            }
            foreign_keys = {
                (row[2], row[3], row[6])
                for row in connection.execute(
                    "PRAGMA foreign_key_list(review_assistance_requests)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(review_assistance_requests)"
                )
            }
            schema = connection.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'review_assistance_requests'"
            ).fetchone()

        assert columns == {
            "id",
            "assignment_id",
            "requested_by_user_id",
            "requested_reviewer_count",
            "reason",
            "status",
            "reviewed_by_user_id",
            "decision_reason",
            "created_at",
            "reviewed_at",
        }
        assert foreign_keys == {
            ("review_assignments", "assignment_id", "RESTRICT"),
            ("users", "requested_by_user_id", "RESTRICT"),
            ("users", "reviewed_by_user_id", "RESTRICT"),
        }
        assert "ix_review_assistance_requests_status_created" in indexes
        assert "uq_review_assistance_requests_pending_assignment" in indexes
        assert schema is not None
        assert "review_assistance_request_status" in schema[0]
        assert "assistance_request_lifecycle" in schema[0]

        command.downgrade(config, "0086_task_foundation")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "review_assistance_requests" not in tables
    finally:
        get_settings.cache_clear()
