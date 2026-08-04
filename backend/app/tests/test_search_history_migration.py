import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_search_history_migration_upgrade_and_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "search-history-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0019_oauth_identities")
    command.upgrade(config, "0020_search_history")

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        entry_indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(search_history_entries)")
        }
    assert {"search_history_preferences", "search_history_entries"}.issubset(tables)
    assert {
        "uq_search_history_entries_user_query_hash",
        "ix_search_history_entries_user_searched",
    }.issubset(entry_indexes)

    command.downgrade(config, "0019_oauth_identities")
    with sqlite3.connect(database_path) as connection:
        remaining = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "search_history_preferences" not in remaining
    assert "search_history_entries" not in remaining
    get_settings.cache_clear()
