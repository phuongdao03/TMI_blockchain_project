import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_membership_benefit_request_migration_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "membership-benefit-requests.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "head")
        with sqlite3.connect(database) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(membership_benefit_requests)"
                )
            }
            assert {
                "user_id",
                "benefit",
                "cycle_started_at",
                "statement",
                "status",
                "decision_note",
            } <= columns
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(membership_benefit_requests)"
                )
            }
            assert "ix_membership_benefit_requests_owner_cycle" in indexes
            assert "ix_membership_benefit_requests_queue" in indexes
            profile_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_profiles)")
            }
            assert {
                "professional_title",
                "organization",
                "activity_fields",
                "professional_links",
            } <= profile_columns
        command.downgrade(config, "0132_membership_catalog_content")
        with sqlite3.connect(database) as connection:
            assert (
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='membership_benefit_requests'"
                ).fetchone()
                is None
            )
            profile_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_profiles)")
            }
            assert (
                not {
                    "professional_title",
                    "organization",
                    "activity_fields",
                    "professional_links",
                }
                & profile_columns
            )
    finally:
        get_settings.cache_clear()
