import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_engagement_analytics_migration_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "engagement-analytics-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0034_engagement_analytics")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(engagement_analytics_snapshots)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(engagement_analytics_snapshots)"
                )
            }
        assert columns == {
            "id",
            "metric_date",
            "generated_at",
            "unique_views",
            "share_events",
            "qr_scans",
            "report_requests",
            "favorite_events",
        }
        assert "ix_engagement_analytics_snapshots_metric_date" in indexes
        # SQLite materializes the named unique constraint as an auto-index.
        assert len(indexes) >= 2
        command.downgrade(config, "0033_public_work_share_events")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "engagement_analytics_snapshots" not in tables
    finally:
        get_settings.cache_clear()
