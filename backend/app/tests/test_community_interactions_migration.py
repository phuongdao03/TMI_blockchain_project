import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_community_interactions_migration_is_reversible(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "community-interactions-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0107_community_write_limits")
        command.upgrade(config, "head")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            post_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_posts)")
            }
            indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(community_profiles)")
            }
            like_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(community_comment_likes)"
                )
            }
        assert "community_comment_likes" in tables
        assert {"view_count"} <= post_columns
        assert {"comment_id", "user_id"} <= like_columns
        assert "uq_community_profiles_username_ci" in indexes

        command.downgrade(config, "0107_community_write_limits")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            post_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_posts)")
            }
            indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(community_profiles)")
            }
        assert "community_comment_likes" not in tables
        assert "view_count" not in post_columns
        assert "uq_community_profiles_username_ci" not in indexes
    finally:
        get_settings.cache_clear()
