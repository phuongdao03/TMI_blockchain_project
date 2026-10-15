import sqlite3
from pathlib import Path
from uuid import UUID

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
EXISTING_USER_ID = UUID("70000000-0000-0000-0000-000000000001")


def test_community_engagement_migration_backfills_safe_profiles_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "community-engagement-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0101_community_foundation")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO users (id, email, status) VALUES (?, ?, ?)",
                (str(EXISTING_USER_ID), "legal-name@example.test", "ACTIVE"),
            )
        command.upgrade(config, "0102_community_engagement")

        with sqlite3.connect(database_path) as connection:
            profile = connection.execute(
                "SELECT username, display_name, avatar_url, bio "
                "FROM community_profiles WHERE user_id = ?",
                (str(EXISTING_USER_ID),),
            ).fetchone()
            unique_indexes = {
                tuple(
                    column[2]
                    for column in connection.execute(
                        f"PRAGMA index_info('{index[1]}')"
                    )
                )
                for index in connection.execute(
                    "PRAGMA index_list(community_likes)"
                )
                if index[2]
            }
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        assert profile == (f"member-{EXISTING_USER_ID.hex}", None, None, None)
        assert ("post_id", "user_id") in unique_indexes
        assert {
            "community_profiles",
            "community_comments",
            "community_likes",
            "community_bookmarks",
            "community_follows",
        } <= tables

        command.downgrade(config, "0101_community_foundation")
        with sqlite3.connect(database_path) as connection:
            remaining_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert not {
            "community_profiles",
            "community_comments",
            "community_likes",
            "community_bookmarks",
            "community_follows",
        }.intersection(remaining_tables)
    finally:
        get_settings.cache_clear()
