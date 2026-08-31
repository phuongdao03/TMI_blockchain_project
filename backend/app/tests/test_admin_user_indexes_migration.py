import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_admin_user_indexes_migration_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "admin-user-indexes.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    expected = {
        "ix_users_created_at",
        "ix_users_status_created_at",
        "ix_users_last_login_at",
        "ix_auth_identities_provider_user_id",
    }
    try:
        command.upgrade(config, "0064_admin_user_indexes")
        with sqlite3.connect(database_path) as connection:
            indexes = {
                row[1]
                for table in ("users", "auth_identities")
                for row in connection.execute(f"PRAGMA index_list({table})")
            }
        assert expected.issubset(indexes)

        command.downgrade(config, "0063_admin_permission_catalog")
        with sqlite3.connect(database_path) as connection:
            remaining = {
                row[1]
                for table in ("users", "auth_identities")
                for row in connection.execute(f"PRAGMA index_list({table})")
            }
        assert expected.isdisjoint(remaining)
    finally:
        get_settings.cache_clear()
