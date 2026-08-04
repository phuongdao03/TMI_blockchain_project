import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_vote_aggregate_and_permission_migrations_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "voting-aggregate-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0025_voting_vote_permissions")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(vote_aggregates)")
        }
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(vote_aggregates)")
        }
        permission = connection.execute(
            "SELECT code FROM permissions WHERE code = 'voting.vote.read'"
        ).fetchone()
    assert columns == {
        "campaign_id",
        "work_id",
        "effective_count",
        "version",
        "refreshed_at",
    }
    assert "ix_vote_aggregates_campaign_count" in indexes
    assert permission == ("voting.vote.read",)

    command.downgrade(config, "0023_voting_permissions")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        permission = connection.execute(
            "SELECT code FROM permissions WHERE code = 'voting.vote.read'"
        ).fetchone()
    assert "vote_aggregates" not in tables
    assert permission is None
    get_settings.cache_clear()
