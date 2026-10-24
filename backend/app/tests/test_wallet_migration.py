import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings


def test_wallet_schema_and_journal_immutability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "wallet.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(Path(__file__).resolve().parents[2] / "alembic.ini")
    try:
        command.upgrade(config, "0128_community_membership")
        command.downgrade(config, "0126_payment_initiator_status_history")
        command.upgrade(config, "0128_community_membership")
        with sqlite3.connect(database) as connection:
            connection.execute(
                "INSERT INTO wallets (user_id, balance_minor) VALUES (?, 1000)",
                ("a" * 32,),
            )
            connection.execute(
                "INSERT INTO wallet_journals (id, user_id, wallet_delta, "
                "counter_delta, balance_after, kind, idempotency_key, "
                "source_reference, description) VALUES "
                "(?, ?, 1000, -1000, 1000, 'TOPUP', 'key', 'source', 'Deposit')",
                ("b" * 32, "a" * 32),
            )
            connection.commit()
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute("UPDATE wallet_journals SET description = 'changed'")
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute("DELETE FROM wallet_journals")
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute("UPDATE wallets SET balance_minor = -1")
        with pytest.raises(RuntimeError, match="financial history"):
            command.downgrade(config, "0126_payment_initiator_status_history")
    finally:
        get_settings.cache_clear()
