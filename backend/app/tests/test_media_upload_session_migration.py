import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "0159_media_upload_sessions"


def test_media_upload_session_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "media-upload-session.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, REVISION)
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
            }
            unique_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(media_assets)")
                if row[2]
            }
        assert "upload_session_id" in columns
        assert any("upload_session_id" in index for index in unique_indexes)

        command.downgrade(config, "0158_community_post_follows")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
            }
        assert "upload_session_id" not in columns
    finally:
        get_settings.cache_clear()
