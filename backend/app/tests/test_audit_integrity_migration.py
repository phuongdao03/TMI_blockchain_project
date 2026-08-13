import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_audit_integrity_migration_is_append_only_and_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "audit-integrity.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0048_audit_integrity")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(audit_logs)")
        }
        triggers = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND tbl_name = 'audit_logs'"
            )
        }
        row_id = connection.execute(
            "INSERT INTO audit_logs (id, actor_type, action, resource_type, "
            "resource_id, created_at) VALUES (?, ?, ?, ?, ?, datetime('now')) "
            "RETURNING id",
            ("audit-row-1", "ANONYMOUS", "test.created", "test", "1"),
        ).fetchone()
        assert row_id == ("audit-row-1",)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE audit_logs SET action = 'test.changed' WHERE id = ?",
                ("audit-row-1",),
            )

    assert {
        "actor_type",
        "actor_service",
        "integrity_version",
        "integrity_key_id",
        "integrity_hash",
        "retention_until",
    }.issubset(columns)
    assert triggers == {
        "trg_audit_logs_reject_update",
        "trg_audit_logs_reject_delete",
    }

    command.downgrade(config, "0047_certificate_version_lifecycle")
    with sqlite3.connect(database_path) as connection:
        downgraded_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(audit_logs)")
        }
    assert "integrity_hash" not in downgraded_columns
    get_settings.cache_clear()
