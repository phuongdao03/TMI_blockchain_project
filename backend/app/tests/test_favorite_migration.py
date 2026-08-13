import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_favorite_migration_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "favorite-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0030_engagement_daily")
        command.upgrade(config, "0031_public_work_favorites")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(public_work_favorites)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(public_work_favorites)"
                )
            }
            foreign_keys = {
                (row[3], row[2], row[4], row[6])
                for row in connection.execute(
                    "PRAGMA foreign_key_list(public_work_favorites)"
                )
            }
            table_sql = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'table' AND name = 'public_work_favorites'
                """
            ).fetchone()[0]

        assert columns == {"id", "user_id", "public_work_id", "created_at"}
        assert "ix_public_work_favorites_work_created" in indexes
        assert ("user_id", "users", "id", "RESTRICT") in foreign_keys
        assert ("public_work_id", "public_works", "id", "RESTRICT") in foreign_keys
        assert "UNIQUE (user_id, public_work_id)" in table_sql

        command.downgrade(config, "0030_engagement_daily")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "public_work_favorites" not in tables
    finally:
        get_settings.cache_clear()
