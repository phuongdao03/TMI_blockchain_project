import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_community_admin_migration_defaults_constraints_permissions_and_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "community-admin-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0102_community_engagement")
        command.upgrade(config, "0103_community_reports_admin")
        with sqlite3.connect(database_path) as connection:
            settings = connection.execute(
                "SELECT singleton_id, pre_moderation_enabled FROM community_settings"
            ).fetchone()
            permission_codes = {
                row[0]
                for row in connection.execute(
                    "SELECT code FROM permissions WHERE code LIKE 'community.%'"
                )
            }
            role_grants = connection.execute(
                "SELECT count(*) FROM role_permissions rp "
                "JOIN permissions p ON p.id = rp.permission_id "
                "WHERE p.code IN ('community.moderate', 'community.manage')"
            ).fetchone()
            report_indexes = {
                row[1]: row[2]
                for row in connection.execute("PRAGMA index_list('community_reports')")
            }
            event_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info('community_moderation_events')"
                )
            }
            comment_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info('community_comments')")
            }
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        assert settings == (1, 1)
        assert {"community.moderate", "community.manage"} <= permission_codes
        assert role_grants == (0,)
        assert report_indexes.get("uq_community_reports_open_reporter_post") == 1
        assert report_indexes.get("uq_community_reports_open_reporter_comment") == 1
        assert {"target_type", "target_id", "report_id"} <= event_columns
        assert "moderation_hidden_at" in comment_columns
        assert {"community_reports", "community_settings"} <= tables

        with sqlite3.connect(database_path) as connection:
            manage_permission_id = connection.execute(
                "SELECT id FROM permissions WHERE code = 'community.manage'"
            ).fetchone()[0]
            role_id = connection.execute("SELECT id FROM roles LIMIT 1").fetchone()[0]
            connection.execute(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                (role_id, manage_permission_id),
            )
            connection.commit()

        command.downgrade(config, "0102_community_engagement")
        with sqlite3.connect(database_path) as connection:
            remaining_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            manage_permission_count = connection.execute(
                "SELECT count(*) FROM permissions WHERE code = 'community.manage'"
            ).fetchone()
        assert not {"community_reports", "community_settings"}.intersection(
            remaining_tables
        )
        assert manage_permission_count == (0,)
        assert "community_posts" in remaining_tables
    finally:
        get_settings.cache_clear()
