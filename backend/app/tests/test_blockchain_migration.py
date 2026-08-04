import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_blockchain_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "blockchain-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0012_blockchain")
    with sqlite3.connect(database_path) as connection:
        assert _columns(connection, "blockchain_transactions") == {
            "id",
            "dossier_id",
            "dossier_version_id",
            "certificate_id",
            "network",
            "chain_id",
            "contract_address",
            "method",
            "payload_hash",
            "tx_hash",
            "nonce",
            "status",
            "confirmations",
            "error_code",
            "error_message",
            "broadcast_at",
            "confirmed_at",
            "created_at",
            "updated_at",
        }
        assert _columns(connection, "certificates") == {
            "id",
            "certificate_number",
            "dossier_id",
            "current_version_no",
            "status",
            "issued_at",
            "expires_at",
            "revoked_at",
            "public_token_hash",
            "pdf_media_id",
            "qr_payload",
            "created_at",
            "updated_at",
        }
        assert _columns(connection, "certificate_versions") == {
            "id",
            "certificate_id",
            "version_no",
            "dossier_version_id",
            "metadata_json",
            "metadata_hash",
            "blockchain_transaction_id",
            "created_at",
        }
        transaction_fks = {
            (row[2], row[3])
            for row in connection.execute(
                "PRAGMA foreign_key_list(blockchain_transactions)"
            )
        }
        assert ("certificates", "certificate_id") in transaction_fks

    command.downgrade(config, "0011_payments")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {
        "blockchain_transactions",
        "certificates",
        "certificate_versions",
    }.isdisjoint(tables)
    get_settings.cache_clear()
