import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CATEGORY_SLUGS = {
    "general",
    "heritage-culture",
    "vietnamese-creativity",
    "people-community",
    "sharing-experiences",
    "feedback-suggestions",
}


def test_community_migration_seeds_categories_without_granting_moderator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "community-migration.sqlite3"
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
            slugs = {
                row[0]
                for row in connection.execute(
                    "SELECT slug FROM community_categories"
                )
            }
            permission = connection.execute(
                "SELECT id FROM permissions WHERE code = 'community.moderate'"
            ).fetchone()
            role_grants = connection.execute(
                "SELECT count(*) FROM role_permissions rp "
                "JOIN permissions p ON p.id = rp.permission_id "
                "WHERE p.code = 'community.moderate'"
            ).fetchone()
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert slugs == EXPECTED_CATEGORY_SLUGS
        assert permission is not None
        assert role_grants == (0,)
        assert {
            "community_categories",
            "community_posts",
            "community_moderation_logs",
        } <= tables

        command.downgrade(config, "0100_video_poster_cache")
        with sqlite3.connect(database_path) as connection:
            remaining_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            permission = connection.execute(
                "SELECT count(*) FROM permissions WHERE code = 'community.moderate'"
            ).fetchone()
        assert not {
            "community_categories",
            "community_posts",
            "community_moderation_logs",
        }.intersection(remaining_tables)
        assert permission == (0,)
    finally:
        get_settings.cache_clear()
