import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_voting_permission_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "voting-permissions.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0023_voting_permissions")

    with sqlite3.connect(database_path) as connection:
        codes = {
            row[0]
            for row in connection.execute(
                "SELECT code FROM permissions WHERE code LIKE 'voting.campaign.%'"
            )
        }
        mappings = connection.execute(
            "SELECT r.code, p.code FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE p.code LIKE 'voting.campaign.%'"
        ).fetchall()
    assert codes == {"voting.campaign.read", "voting.campaign.manage"}
    assert set(mappings) == {
        (role, permission)
        for role in ("CONTENT_ADMIN", "SUPER_ADMIN")
        for permission in codes
    }

    command.downgrade(config, "0022_voting_foundation")
    with sqlite3.connect(database_path) as connection:
        remaining = connection.execute(
            "SELECT count(*) FROM permissions WHERE code LIKE 'voting.campaign.%'"
        ).fetchone()
    assert remaining == (0,)
    get_settings.cache_clear()
