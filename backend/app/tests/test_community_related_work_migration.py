import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_community_related_work_migration_adds_nullable_set_null_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "community-related-work-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0103_community_reports_admin")
        command.upgrade(config, "0104_community_related_work")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info('community_posts')")
            }
            indexes = {
                row[1]: row[2]
                for row in connection.execute("PRAGMA index_list('community_posts')")
            }
            foreign_keys = list(
                connection.execute("PRAGMA foreign_key_list('community_posts')")
            )
        assert "related_work_id" in columns
        assert indexes.get("ix_community_posts_related_work_id") == 0
        assert any(
            row[2] == "public_works" and row[6] == "SET NULL" for row in foreign_keys
        )

        command.downgrade(config, "0103_community_reports_admin")
        with sqlite3.connect(database_path) as connection:
            columns_after = {
                row[1]
                for row in connection.execute("PRAGMA table_info('community_posts')")
            }
        assert "related_work_id" not in columns_after
    finally:
        get_settings.cache_clear()
