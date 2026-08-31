import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_price_catalog_migration_is_reversible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "price-catalog.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0067_billing_price_catalog")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"price_catalog_versions", "price_catalog_entries"}.issubset(
            tables
        )
        entry_indexes = {
            row[1]
            for row in connection.execute(
                "PRAGMA index_list(price_catalog_entries)"
            )
        }
        assert "ix_price_catalog_entries_dossier_type_id" in entry_indexes

    command.downgrade(config, "0066_type_specific_review_rubric")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "price_catalog_entries" not in tables
        assert "price_catalog_versions" not in tables
    get_settings.cache_clear()
