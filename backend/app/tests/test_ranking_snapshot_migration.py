import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_ranking_snapshot_migration_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "ranking-snapshot-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0026_ranking_snapshots")

    with sqlite3.connect(database_path) as connection:
        snapshot_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(ranking_snapshots)")
        }
        item_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(ranking_snapshot_items)")
        }
        snapshot_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(ranking_snapshots)")
        }
        item_indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(ranking_snapshot_items)")
        }

    assert snapshot_columns == {
        "id",
        "campaign_id",
        "version",
        "formula_version",
        "campaign_rule_version",
        "source_digest",
        "result_digest",
        "candidate_count",
        "total_valid_votes",
        "created_at",
    }
    assert item_columns == {
        "snapshot_id",
        "work_id",
        "rank",
        "display_order",
        "score",
        "effective_vote_count",
    }
    assert "ix_ranking_snapshots_campaign_created" in snapshot_indexes
    assert "ix_ranking_snapshot_items_snapshot_rank" in item_indexes

    command.downgrade(config, "0025_voting_vote_permissions")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "ranking_snapshots" not in tables
    assert "ranking_snapshot_items" not in tables
    get_settings.cache_clear()
