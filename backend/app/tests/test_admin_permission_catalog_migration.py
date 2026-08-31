import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]

ADMIN_PERMISSION_CODES = {
    "dashboard.read",
    "users.read",
    "users.update",
    "users.suspend",
    "users.sessions.revoke",
    "staff.read",
    "staff.invite",
    "staff.update",
    "staff.permissions.assign",
    "submissions.read",
    "submissions.review",
    "submissions.approve",
    "submissions.reject",
    "payments.read",
    "payments.reconcile",
    "payments.refund",
    "payments.export",
    "blockchain.read",
    "blockchain.retry",
    "storage.read",
    "storage.delete",
    "security.read",
    "security.manage",
    "system.read",
    "system.manage",
    "reports.read",
    "reports.export",
    "settings.read",
    "settings.manage",
}


def test_admin_permission_catalog_does_not_grant_privilege(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "admin-permission-catalog.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0063_admin_permission_catalog")
        with sqlite3.connect(database_path) as connection:
            codes = {
                row[0]
                for row in connection.execute(
                    "SELECT code FROM permissions WHERE code IN ("
                    + ",".join("?" for _ in ADMIN_PERMISSION_CODES)
                    + ")",
                    tuple(ADMIN_PERMISSION_CODES),
                )
            }
            role_grants = connection.execute(
                "SELECT count(*) FROM role_permissions rp "
                "JOIN permissions p ON p.id = rp.permission_id WHERE p.code IN ("
                + ",".join("?" for _ in ADMIN_PERMISSION_CODES)
                + ")",
                tuple(ADMIN_PERMISSION_CODES),
            ).fetchone()
            user_grants = connection.execute(
                "SELECT count(*) FROM user_permissions"
            ).fetchone()
        assert codes == ADMIN_PERMISSION_CODES
        assert role_grants == (0,)
        assert user_grants == (0,)

        command.downgrade(config, "0062_user_permissions")
        with sqlite3.connect(database_path) as connection:
            remaining = connection.execute(
                "SELECT count(*) FROM permissions WHERE code IN ("
                + ",".join("?" for _ in ADMIN_PERMISSION_CODES)
                + ")",
                tuple(ADMIN_PERMISSION_CODES),
            ).fetchone()
        assert remaining == (0,)
    finally:
        get_settings.cache_clear()
