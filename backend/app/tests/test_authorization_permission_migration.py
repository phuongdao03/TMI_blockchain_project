import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_authorization_permission_catalog_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "authorization-permissions.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0042_authorization_permissions")

    with sqlite3.connect(database_path) as connection:
        mappings = set(
            connection.execute(
                "SELECT r.code, p.code FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id "
                "JOIN permissions p ON p.id = rp.permission_id "
                "WHERE p.code NOT LIKE 'voting.%'"
            ).fetchall()
        )
    expected = {
        "admin.staff.manage": {"SUPER_ADMIN"},
        "audit.read": {"SUPER_ADMIN"},
        "blockchain.manage": {"BLOCKCHAIN_ADMIN", "SUPER_ADMIN"},
        "certificate.read": {"APPLICANT", "ORG_MANAGER", "SUPER_ADMIN"},
        "cms.manage": {"CONTENT_ADMIN", "SUPER_ADMIN"},
        "council.manage": {"COUNCIL_SECRETARY", "SUPER_ADMIN"},
        "council.vote": {"COUNCIL_MEMBER"},
        "dossier.manage": {"APPLICANT", "ORG_MANAGER"},
        "engagement.qr.manage": {"CONTENT_ADMIN", "SUPER_ADMIN"},
        "operations.read": {"FINANCE_ADMIN", "BLOCKCHAIN_ADMIN", "SUPER_ADMIN"},
        "payment.create": {"APPLICANT", "ORG_MANAGER"},
        "payment.manage": {"FINANCE_ADMIN", "SUPER_ADMIN"},
        "public_content.manage": {"CONTENT_ADMIN", "SUPER_ADMIN"},
        "ranking.manage": {"SUPER_ADMIN"},
        "review.assign": {"SUPER_ADMIN"},
        "review.submit": {"REVIEWER"},
        "search.analytics.read": {"CONTENT_ADMIN", "SUPER_ADMIN"},
    }
    assert mappings == {
        (role, permission) for permission, roles in expected.items() for role in roles
    }

    command.downgrade(config, "0041_blockchain_receipt_provenance")
    with sqlite3.connect(database_path) as connection:
        remaining = connection.execute(
            "SELECT count(*) FROM permissions WHERE code IN ("
            + ",".join("?" for _ in expected)
            + ")",
            tuple(expected),
        ).fetchone()
    assert remaining == (0,)
    get_settings.cache_clear()
