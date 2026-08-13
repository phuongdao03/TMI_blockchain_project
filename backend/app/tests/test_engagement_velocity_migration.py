import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_engagement_velocity_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "engagement-velocity-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0035_engagement_velocity")
        with sqlite3.connect(database_path) as connection:
            assert {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            } >= {
                "engagement_velocity_snapshots",
                "engagement_velocity_snapshot_items",
            }
            assert {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(engagement_velocity_snapshot_items)"
                )
            } >= {"ix_engagement_velocity_snapshot_items_snapshot_rank"}

            command.downgrade(config, "0034_engagement_analytics")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            assert "engagement_velocity_snapshots" not in tables
            assert "engagement_velocity_snapshot_items" not in tables
            assert (
                connection.execute(
                    "SELECT version_num FROM alembic_version"
                ).fetchone()[0]
                == "0034_engagement_analytics"
            )
    finally:
        get_settings.cache_clear()
