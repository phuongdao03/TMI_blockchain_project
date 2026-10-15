import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_community_tags_migration_adds_constraints_and_downgrades_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "community-tags-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0105_community_post_media")
        command.upgrade(config, "0106_community_post_tags")
        with sqlite3.connect(database_path) as connection:
            tag_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info('community_tags')"
                )
            }
            relation_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info('community_post_tags')"
                )
            }
            tag_indexes = list(
                connection.execute("PRAGMA index_list('community_tags')")
            )
            relation_indexes = list(
                connection.execute("PRAGMA index_list('community_post_tags')")
            )
            relation_foreign_keys = list(
                connection.execute("PRAGMA foreign_key_list('community_post_tags')")
            )
        assert {"id", "name", "slug", "created_at", "updated_at"} <= tag_columns
        assert {"post_id", "tag_id"} <= relation_columns
        assert any(row[2] for row in tag_indexes)
        assert any(row[2] for row in relation_indexes)
        assert {row[2] for row in relation_foreign_keys} == {
            "community_posts",
            "community_tags",
        }

        command.downgrade(config, "0105_community_post_media")
        with sqlite3.connect(database_path) as connection:
            tables_after = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert "community_tags" not in tables_after
        assert "community_post_tags" not in tables_after
    finally:
        get_settings.cache_clear()
