import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_fee_obligation_migration_is_reversible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "fee-obligations.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0068_fee_obligations")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(fee_obligations)")
        }
        assert {
            "dossier_id",
            "owner_user_id",
            "amount_minor",
            "price_snapshot_json",
            "due_at",
        }.issubset(columns)
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(fee_obligations)")
        }
        assert "ix_fee_obligations_owner_status_due" in indexes

    command.downgrade(config, "0067_billing_price_catalog")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "fee_obligations" not in tables
        assert "price_catalog_entries" in tables
    get_settings.cache_clear()
