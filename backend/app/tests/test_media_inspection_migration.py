import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_media_inspection_migration_adds_fail_closed_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "media-inspection.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0044_secure_media_inspection")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
        table_sql_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='media_assets'"
        ).fetchone()
        assert table_sql_row is not None
        table_sql = table_sql_row[0]

    assert {
        "inspection_attempts",
        "inspection_reason_code",
        "inspected_at",
    }.issubset(columns)
    assert "REJECTED" in table_sql
    assert "inspection_attempts >= 0" in table_sql

    command.downgrade(config, "0043_staff_privileged_actions")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
        table_sql_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='media_assets'"
        ).fetchone()
        assert table_sql_row is not None
        table_sql = table_sql_row[0]
    assert "inspection_attempts" not in columns
    assert "REJECTED" not in table_sql
    get_settings.cache_clear()
