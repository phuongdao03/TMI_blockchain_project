import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_content_report_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "content-reports.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0017_content_reports")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(content_reports)")
        }
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(content_reports)")
        }
    assert {
        "id",
        "public_work_id",
        "reporter_user_id",
        "reporter_email_hash",
        "reporter_email_encrypted",
        "reason",
        "description",
        "dedup_key",
        "reporter_ip_hash",
        "status",
        "assigned_to_user_id",
        "resolution_note",
        "resolved_at",
        "created_at",
        "updated_at",
    } == columns
    assert "ix_content_reports_status_created" in indexes
    assert "ix_content_reports_work_created" in indexes

    command.downgrade(config, "0016_public_media")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "content_reports" not in tables
    get_settings.cache_clear()
