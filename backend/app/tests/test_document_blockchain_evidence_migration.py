import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_document_blockchain_evidence_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "document-blockchain-evidence.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0053_document_blockchain_evidence")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(document_blockchain_evidences)"
            )
        }
        transaction_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(blockchain_transactions)")
        }

    assert {
        "document_hash_claim_id",
        "evidence_key",
        "commitment",
        "submitter_reference",
        "version_no",
        "predecessor_evidence_id",
        "recorded_at",
        "status",
    }.issubset(columns)
    assert "document_evidence_id" in transaction_columns

    command.downgrade(config, "0052_document_hash_claims")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        transaction_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(blockchain_transactions)")
        }
    assert "document_blockchain_evidences" not in tables
    assert "document_evidence_id" not in transaction_columns
    get_settings.cache_clear()
