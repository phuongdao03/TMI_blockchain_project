import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_certificate_version_lifecycle_schema_and_permissions_are_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "certificate-version-lifecycle.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0047_certificate_version_lifecycle")
    with sqlite3.connect(database_path) as connection:
        version_columns = _columns(connection, "certificate_versions")
        certificate_columns = _columns(connection, "certificates")
        indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(certificate_versions)")
        }
        permissions = connection.execute(
            "SELECT r.code, p.code FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE p.code IN "
            "('certificate.version.request', 'certificate.version.decide') "
            "ORDER BY p.code, r.code"
        ).fetchall()

    assert {
        "predecessor_version_id",
        "status",
        "change_reason",
        "requested_by",
        "requested_at",
        "decided_by",
        "decided_at",
        "rejection_reason",
        "pdf_media_id",
        "revoked_at",
    }.issubset(version_columns)
    assert {"revocation_reason_hash", "revocation_transaction_id"}.issubset(
        certificate_columns
    )
    assert {
        "uq_certificate_versions_active",
        "uq_certificate_versions_open_request",
    }.issubset(indexes)
    assert permissions == [
        ("SUPER_ADMIN", "certificate.version.decide"),
        ("APPLICANT", "certificate.version.request"),
        ("ORG_MANAGER", "certificate.version.request"),
    ]

    command.downgrade(config, "0046_similarity_review_cases")
    with sqlite3.connect(database_path) as connection:
        assert "status" not in _columns(connection, "certificate_versions")
        assert "revocation_reason_hash" not in _columns(connection, "certificates")
        assert connection.execute(
            "SELECT count(*) FROM permissions WHERE code IN "
            "('certificate.version.request', 'certificate.version.decide')"
        ).fetchone() == (0,)
    get_settings.cache_clear()
