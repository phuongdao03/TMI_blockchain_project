import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_engagement_daily_migration_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "engagement-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0029_ranking_publication")
        command.upgrade(config, "0030_public_work_engagement_daily")

        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]: (row[2], row[3], row[4])
                for row in connection.execute(
                    "PRAGMA table_info(public_work_engagement_daily)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(public_work_engagement_daily)"
                )
            }
            foreign_keys = {
                (row[3], row[2], row[4], row[6])
                for row in connection.execute(
                    "PRAGMA foreign_key_list(public_work_engagement_daily)"
                )
            }
            table_sql = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'table' AND name = 'public_work_engagement_daily'
                """
            ).fetchone()[0]

        assert set(columns) == {
            "public_work_id",
            "metric_date",
            "unique_views",
            "share_events",
            "qr_scans",
            "report_requests",
            "created_at",
            "updated_at",
        }
        assert columns["unique_views"][2].strip("'") == "0"
        assert columns["share_events"][2].strip("'") == "0"
        assert columns["qr_scans"][2].strip("'") == "0"
        assert columns["report_requests"][2].strip("'") == "0"
        assert "ix_public_work_engagement_daily_date_work" in indexes
        assert ("public_work_id", "public_works", "id", "RESTRICT") in foreign_keys
        assert "unique_views >= 0" in table_sql
        assert "share_events >= 0" in table_sql
        assert "qr_scans >= 0" in table_sql
        assert "report_requests >= 0" in table_sql

        command.downgrade(config, "0029_ranking_publication")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "public_work_engagement_daily" not in tables
    finally:
        get_settings.cache_clear()
