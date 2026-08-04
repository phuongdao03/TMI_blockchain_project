import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_user_profile_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "user-profile-migration.sqlite3"
    direct_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_DIRECT_URL", direct_url)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0004_user_profiles")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(user_profiles)")
        }
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(user_profiles)"
        ).fetchall()
    assert columns == {
        "user_id",
        "full_name",
        "phone_encrypted",
        "avatar_media_id",
        "locale",
        "timezone",
        "created_at",
        "updated_at",
    }
    assert any(row[2] == "users" and row[3] == "user_id" for row in foreign_keys)

    command.downgrade(config, "0003_registration_outbox")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "user_profiles" not in tables
    get_settings.cache_clear()
