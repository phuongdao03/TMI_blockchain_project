import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_checkout_link_migration_is_reversible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "billing-checkout.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0069_billing_checkout_link")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(payment_orders)")
        }
        assert "fee_obligation_id" in columns
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(payment_orders)")
        }
        assert "ix_payment_orders_fee_obligation_id" in indexes

    command.downgrade(config, "0068_fee_obligations")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(payment_orders)")
        }
        assert "fee_obligation_id" not in columns
    get_settings.cache_clear()
