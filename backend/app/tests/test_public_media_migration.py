import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_public_media_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "public-media.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0016_public_media")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(public_work_media)")
        }
        indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(public_work_media)")
        }
    assert {
        "id",
        "public_work_id",
        "media_asset_id",
        "media_kind",
        "sort_order",
        "caption",
        "alt_text",
        "derivative_status",
        "derivative_url",
        "derivative_public_id",
        "derivative_mime_type",
        "derivative_width",
        "derivative_height",
        "duration_ms",
        "attempt_count",
        "failure_code",
        "created_at",
        "updated_at",
    } == columns
    assert "ix_public_work_media_work_order" in indexes

    command.downgrade(config, "0015_public_taxonomy")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "public_work_media" not in tables
    get_settings.cache_clear()
