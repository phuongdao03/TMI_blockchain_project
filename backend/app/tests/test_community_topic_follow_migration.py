import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_community_topic_follow_migration_is_additive_and_reversible(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "community-topic-follow-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0158_community_post_follows")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(community_post_follows)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(community_post_follows)"
                )
            }
            unique_indexes = [
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(community_post_follows)"
                )
                if row[2]
            ]
            unique_columns = {
                tuple(
                    item[2]
                    for item in connection.execute(
                        f'PRAGMA index_info("{index_name}")'
                    )
                )
                for index_name in unique_indexes
            }
        assert "community_posts" in tables
        assert "community_comments" in tables
        assert {"id", "post_id", "user_id", "created_at"} <= columns
        assert ("post_id", "user_id") in unique_columns
        assert "ix_community_post_follows_user_created" in indexes

        command.downgrade(config, "0157_wallet_topup_terms")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "community_post_follows" not in tables
        assert "community_posts" in tables
        assert "community_comments" in tables
    finally:
        get_settings.cache_clear()
