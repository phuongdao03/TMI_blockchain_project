import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_share_link_migration_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "share-link-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0032_public_share_links")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(public_share_links)"
                )
            }
            foreign_keys = {
                (row[3], row[2], row[4], row[6])
                for row in connection.execute(
                    "PRAGMA foreign_key_list(public_share_links)"
                )
            }
        assert columns == {
            "id",
            "public_work_id",
            "token_hash",
            "created_at",
            "revoked_at",
        }
        assert ("public_work_id", "public_works", "id", "RESTRICT") in foreign_keys
        command.downgrade(config, "0031_public_work_favorites")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "public_share_links" not in tables
    finally:
        get_settings.cache_clear()
