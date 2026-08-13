import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_staff_privileged_action_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "staff-privileged-actions.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0043_staff_privileged_actions")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(privileged_actions)")
        }
        user_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(users)")
        }
        permission_roles = connection.execute(
            "SELECT r.code FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE p.code = 'admin.staff.approve'"
        ).fetchall()
    assert {
        "target_user_id",
        "action_type",
        "status",
        "requested_by_user_id",
        "approved_by_user_id",
        "expires_at",
    }.issubset(columns)
    assert "disabled_at" in user_columns
    assert permission_roles == [("SUPER_ADMIN",)]

    command.downgrade(config, "0042_authorization_permissions")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        user_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(users)")
        }
    assert "privileged_actions" not in tables
    assert "disabled_at" not in user_columns
    get_settings.cache_clear()
