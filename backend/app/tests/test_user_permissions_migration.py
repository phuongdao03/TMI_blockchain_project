import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_user_permissions_migration_is_additive_and_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "user-permissions.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0062_user_permissions")

        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]: (row[2], row[3], row[5])
                for row in connection.execute("PRAGMA table_info(user_permissions)")
            }
            foreign_keys = {
                (row[3], row[2], row[4], row[6])
                for row in connection.execute(
                    "PRAGMA foreign_key_list(user_permissions)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(user_permissions)")
            }
            assignments = connection.execute(
                "SELECT count(*) FROM user_permissions"
            ).fetchone()
            revision_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(user_permission_revisions)"
                )
            }

        assert set(columns) == {
            "user_id",
            "permission_id",
            "granted_by_user_id",
            "reason",
            "expires_at",
            "version",
            "created_at",
            "updated_at",
        }
        assert columns["user_id"][2] == 1
        assert columns["permission_id"][2] == 2
        assert ("user_id", "users", "id", "CASCADE") in foreign_keys
        assert ("permission_id", "permissions", "id", "CASCADE") in foreign_keys
        assert (
            "granted_by_user_id",
            "users",
            "id",
            "RESTRICT",
        ) in foreign_keys
        assert "ix_user_permissions_permission_id" in indexes
        assert "ix_user_permissions_user_expires" in indexes
        assert assignments == (0,)
        assert revision_columns == {
            "user_id",
            "version",
            "updated_by_user_id",
            "reason",
            "created_at",
            "updated_at",
        }

        command.downgrade(config, "0061_moderator_permissions")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "user_permissions" not in tables
        assert "user_permission_revisions" not in tables
    finally:
        get_settings.cache_clear()
