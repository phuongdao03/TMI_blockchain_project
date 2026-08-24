import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_human_signing_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "human-signing.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0057_blockchain_human_signing")
    with sqlite3.connect(database_path) as connection:
        transaction_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(blockchain_transactions)")
        }
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        permission_codes = {
            row[0]
            for row in connection.execute(
                "SELECT code FROM permissions WHERE code = 'blockchain.sign'"
            )
        }

    assert {"signer_user_id", "signer_wallet_address"}.issubset(transaction_columns)
    assert {
        "blockchain_wallet_links",
        "blockchain_wallet_challenges",
        "blockchain_transaction_intents",
    }.issubset(tables)
    assert permission_codes == {"blockchain.sign"}

    command.downgrade(config, "0056_review_assessment_findings")
    with sqlite3.connect(database_path) as connection:
        transaction_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(blockchain_transactions)")
        }
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"signer_user_id", "signer_wallet_address"}.isdisjoint(transaction_columns)
    assert "blockchain_wallet_links" not in tables
    get_settings.cache_clear()
