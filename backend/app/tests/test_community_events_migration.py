import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_community_events_migration_round_trip(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "community-events.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0130_community_events")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            registration_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(community_event_registrations)"
                )
            }
            event_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_events)")
            }
        assert "community_events" in tables
        assert "community_event_registrations" in tables
        assert "confirmed_count" in event_columns
        assert (
            "uq_community_event_registrations_active_user_event" in registration_indexes
        )
        with sqlite3.connect(database_path) as connection:
            quota_policies = connection.execute(
                "SELECT tier, entitlement, quota_count "
                "FROM membership_event_entitlement_policies "
                "ORDER BY tier, entitlement"
            ).fetchall()
        assert quota_policies == [
            ("COMPANION", "CONNECT", 6),
            ("COMPANION", "TALK", 4),
            ("PRESTIGE", "CIRCLE", 2),
            ("PRESTIGE", "CONNECT", 6),
            ("PRESTIGE", "TALK", 4),
            ("SILVER", "TALK", 4),
        ]

        command.downgrade(config, "0129_membership_tiers_and_diamond_applications")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "community_events" not in tables
        assert "community_event_registrations" not in tables
    finally:
        get_settings.cache_clear()


def test_event_priority_window_migration_round_trip(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "community-event-priority.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "head")
        with sqlite3.connect(database_path) as connection:
            event_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_events)")
            }
        assert {
            "registration_opens_at",
            "priority_tier",
            "priority_opens_at",
        } <= event_columns

        command.downgrade(config, "0134_membership_professional_profiles")
        with sqlite3.connect(database_path) as connection:
            event_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(community_events)")
            }
        assert not {
            "registration_opens_at",
            "priority_tier",
            "priority_opens_at",
        } & event_columns
    finally:
        get_settings.cache_clear()
