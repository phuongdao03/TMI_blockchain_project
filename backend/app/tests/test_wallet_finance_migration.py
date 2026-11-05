import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings


def test_finance_journal_is_immutable_and_migration_refuses_data_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "finance.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(Path(__file__).resolve().parents[2] / "alembic.ini")
    try:
        command.upgrade(config, "0155_finance_permissions")
        with sqlite3.connect(database) as connection:
            settings = connection.execute(
                "SELECT withdrawal_enabled, payout_live_enabled, daily_limit_minor, "
                "daily_count_limit, approval_required "
                "FROM finance_settings WHERE id = 1"
            ).fetchone()
            assert settings == (0, 0, 0, 0, 1)
            assert connection.execute(
                "SELECT COUNT(*) FROM permissions WHERE code LIKE 'finance.%' "
                "OR code LIKE 'affiliate.%'"
            ).fetchone() == (10,)
            connection.execute(
                "INSERT INTO finance_accounts "
                "(id, account_type, account_code, currency) "
                "VALUES (?, 'COMMISSION_EXPENSE', 'platform:expense', 'VND')",
                ("a" * 32,),
            )
            connection.execute(
                "INSERT INTO finance_accounts "
                "(id, account_type, account_code, currency) "
                "VALUES (?, 'COMMISSION_AVAILABLE', 'affiliate:available', 'VND')",
                ("b" * 32,),
            )
            connection.execute(
                "INSERT INTO finance_journals "
                "(id, transaction_type, idempotency_key, source_reference, "
                "description) "
                "VALUES (?, 'COMMISSION_CREDIT', 'credit-key', 'commission:1', "
                "'Credit')",
                ("c" * 32,),
            )
            connection.executemany(
                "INSERT INTO finance_entries "
                "(id, journal_id, account_id, amount_minor) "
                "VALUES (?, ?, ?, ?)",
                [
                    ("d" * 32, "c" * 32, "a" * 32, -1000),
                    ("e" * 32, "c" * 32, "b" * 32, 1000),
                ],
            )
            connection.commit()
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute("UPDATE finance_entries SET amount_minor = 2000")
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute("DELETE FROM finance_journals")
        with pytest.raises(RuntimeError, match="Finance ledger history"):
            command.downgrade(config, "0152_structured_supplements")
    finally:
        get_settings.cache_clear()
