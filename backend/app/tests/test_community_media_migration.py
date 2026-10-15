import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_community_media_migration_keeps_legacy_purpose_null_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "community-media-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0104_community_related_work")
        command.upgrade(config, "0105_community_post_media")
        with sqlite3.connect(database_path) as connection:
            media_columns = {
                row[1]: row
                for row in connection.execute("PRAGMA table_info('media_assets')")
            }
            relation_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info('community_post_media')"
                )
            }
            relation_indexes = list(
                connection.execute("PRAGMA index_list('community_post_media')")
            )
            relation_foreign_keys = list(
                connection.execute("PRAGMA foreign_key_list('community_post_media')")
            )
        assert "purpose" in media_columns
        assert media_columns["purpose"][3] == 0
        assert {"post_id", "media_asset_id", "sort_order"} <= relation_columns
        assert any(row[2] for row in relation_indexes)
        assert {row[2] for row in relation_foreign_keys} == {
            "community_posts",
            "media_assets",
        }

        command.downgrade(config, "0104_community_related_work")
        with sqlite3.connect(database_path) as connection:
            media_columns_after = {
                row[1]
                for row in connection.execute("PRAGMA table_info('media_assets')")
            }
            tables_after = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert "purpose" not in media_columns_after
        assert "community_post_media" not in tables_after
    finally:
        get_settings.cache_clear()
