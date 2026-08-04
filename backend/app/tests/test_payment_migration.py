import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_payment_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "payment-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0011_payments")

    with sqlite3.connect(database_path) as connection:
        assert _columns(connection, "payment_orders") == {
            "id",
            "order_code",
            "dossier_id",
            "provider",
            "provider_order_id",
            "amount_minor",
            "currency",
            "status",
            "expires_at",
            "paid_at",
            "idempotency_key",
            "metadata",
            "created_at",
            "updated_at",
        }
        assert _columns(connection, "payment_events") == {
            "id",
            "payment_order_id",
            "provider_event_id",
            "event_type",
            "signature_valid",
            "payload_redacted",
            "received_at",
            "processed_at",
        }

    command.downgrade(config, "0010_council")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "payment_orders" not in tables
    assert "payment_events" not in tables
    get_settings.cache_clear()
