import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_ranking_publication_migration_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "ranking-publication-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0028_trending_snapshots")
    command.upgrade(config, "0029_ranking_publication")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(voting_campaigns)")
        }
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(voting_campaigns)")
        }
        foreign_keys = {
            (row[3], row[2], row[4], row[6])
            for row in connection.execute("PRAGMA foreign_key_list(voting_campaigns)")
        }

    assert "published_snapshot_id" in columns
    assert "results_published_at" in columns
    assert "ix_voting_campaigns_published_snapshot_id" in indexes
    assert (
        "published_snapshot_id",
        "ranking_snapshots",
        "id",
        "RESTRICT",
    ) in foreign_keys

    command.downgrade(config, "0028_trending_snapshots")
    with sqlite3.connect(database_path) as connection:
        columns_after = {
            row[1] for row in connection.execute("PRAGMA table_info(voting_campaigns)")
        }
    assert "published_snapshot_id" not in columns_after
    assert "results_published_at" not in columns_after
    get_settings.cache_clear()
