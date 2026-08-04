import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_organization_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "organization-migration.sqlite3"
    direct_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_DIRECT_URL", direct_url)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0005_organizations")

    with sqlite3.connect(database_path) as connection:
        organization_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(organizations)")
        }
        member_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(organization_members)")
        }
        member_indexes = connection.execute(
            "PRAGMA index_list(organization_members)"
        ).fetchall()
    assert organization_columns == {
        "id",
        "code",
        "legal_name",
        "display_name",
        "tax_code_encrypted",
        "status",
        "owner_user_id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert member_columns == {
        "organization_id",
        "user_id",
        "role_code",
        "status",
        "joined_at",
        "created_at",
        "updated_at",
    }
    assert any(row[1] == "ix_organization_members_user_id" for row in member_indexes)

    command.downgrade(config, "0004_user_profiles")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "organizations" not in tables
    assert "organization_members" not in tables
    get_settings.cache_clear()
