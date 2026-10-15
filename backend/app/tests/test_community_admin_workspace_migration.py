import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_community_admin_workspace_migration_is_reversible(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "community-admin-workspace.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0108_community_interactions")
        command.upgrade(config, "head")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            post_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_posts)")
            }
            comment_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(community_comments)"
                )
            }
            event_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' "
                "AND name='community_moderation_events'"
            ).fetchone()[0]
        assert "community_member_restrictions" in tables
        assert {
            "pinned_at",
            "comments_locked_at",
            "pre_delete_status",
            "admin_deleted",
        } <= post_columns
        assert {"admin_deleted", "pre_delete_hidden_at"} <= comment_columns
        assert "MEMBER_RESTRICTION_REVOKED" in event_sql

        command.downgrade(config, "0108_community_interactions")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            post_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_posts)")
            }
            comment_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(community_comments)"
                )
            }
            event_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' "
                "AND name='community_moderation_events'"
            ).fetchone()[0]
        assert "community_member_restrictions" not in tables
        assert not {
            "pinned_at",
            "comments_locked_at",
            "pre_delete_status",
            "admin_deleted",
        }.intersection(post_columns)
        assert not {"admin_deleted", "pre_delete_hidden_at"}.intersection(
            comment_columns
        )
        assert "MEMBER_RESTRICTION_REVOKED" in event_sql
    finally:
        get_settings.cache_clear()
