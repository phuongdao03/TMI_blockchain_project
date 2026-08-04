import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_voting_migration_upgrades_exact_schema_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "voting-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0022_voting_foundation")

    expected_columns = {
        "voting_campaigns": {
            "id",
            "name",
            "slug",
            "description",
            "status",
            "campaign_type",
            "period_type",
            "timezone",
            "start_at",
            "end_at",
            "max_votes_per_user",
            "max_votes_per_work_per_user",
            "allow_vote_change",
            "allow_vote_revoke",
            "require_verified_email",
            "min_account_age_hours",
            "eligibility_rules",
            "rule_version",
            "created_by",
            "created_at",
            "updated_at",
        },
        "campaign_works": {
            "id",
            "campaign_id",
            "work_id",
            "status",
            "approved_by",
            "approved_at",
            "metadata",
            "created_at",
            "updated_at",
        },
        "votes": {
            "id",
            "campaign_id",
            "work_id",
            "user_id",
            "status",
            "source",
            "idempotency_key",
            "risk_score",
            "created_at",
            "updated_at",
            "revoked_at",
        },
        "vote_events": {
            "id",
            "vote_id",
            "event_type",
            "actor_user_id",
            "reason",
            "metadata",
            "created_at",
        },
        "campaign_events": {
            "id",
            "campaign_id",
            "event_type",
            "actor_user_id",
            "reason",
            "before_snapshot",
            "after_snapshot",
            "created_at",
        },
    }
    with sqlite3.connect(database_path) as connection:
        for table, columns in expected_columns.items():
            assert _columns(connection, table) == columns

        campaign_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='voting_campaigns'"
        ).fetchone()
        vote_indexes = connection.execute("PRAGMA index_list(votes)").fetchall()
        unique_vote_columns = {
            tuple(
                item[2] for item in connection.execute(f'PRAGMA index_info("{row[1]}")')
            )
            for row in vote_indexes
            if row[2] == 1
        }
        effective_index_sql = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='index' AND name='uq_votes_effective_campaign_work_user'"
        ).fetchone()
        campaign_plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT id FROM voting_campaigns "
            "WHERE status = 'ACTIVE' AND start_at <= CURRENT_TIMESTAMP "
            "AND end_at > CURRENT_TIMESTAMP"
        ).fetchall()
        quota_plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT count(*) FROM votes "
            "WHERE campaign_id = ? AND work_id = ? AND status = 'VALID'",
            ("campaign-id", "work-id"),
        ).fetchall()

    assert campaign_sql is not None
    assert "time_window_valid" in campaign_sql[0]
    assert "max_votes_per_work_one" in campaign_sql[0]
    assert ("user_id", "idempotency_key") in unique_vote_columns
    assert effective_index_sql is not None
    assert "WHERE status IN ('VALID', 'SUSPICIOUS')" in effective_index_sql[0]
    assert any("ix_voting_campaigns_status_window" in row[3] for row in campaign_plan)
    assert any("ix_votes_campaign_work_status" in row[3] for row in quota_plan)

    command.downgrade(config, "0021_search_discovery")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert not set(expected_columns).intersection(tables)
    assert "search_events" in tables
    get_settings.cache_clear()
