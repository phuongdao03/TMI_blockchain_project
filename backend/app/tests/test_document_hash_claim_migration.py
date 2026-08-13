import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_document_hash_claim_migration_is_reversible_and_seeds_permission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "document-hash-claims.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0052_document_hash_claims")

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        permission_roles = connection.execute(
            "SELECT r.code FROM roles r "
            "JOIN role_permissions rp ON rp.role_id = r.id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE p.code = 'document_claim.override'"
        ).fetchall()

    assert {
        "document_hash_anchors",
        "document_hash_claims",
        "document_hash_adjudications",
    }.issubset(tables)
    assert permission_roles == [("SUPER_ADMIN",)]

    command.downgrade(config, "0051_private_media_encryption")
    with sqlite3.connect(database_path) as connection:
        remaining = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        permission = connection.execute(
            "SELECT 1 FROM permissions WHERE code = 'document_claim.override'"
        ).fetchone()
    assert "document_hash_anchors" not in remaining
    assert "document_hash_claims" not in remaining
    assert "document_hash_adjudications" not in remaining
    assert permission is None
    get_settings.cache_clear()
