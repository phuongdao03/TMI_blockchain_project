import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_council_migration_upgrades_exact_schema_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "council-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0010_council")

    expected_columns = {
        "council_sessions": {
            "id",
            "code",
            "title",
            "scheduled_at",
            "status",
            "quorum_required",
            "opened_at",
            "closed_at",
            "minutes_hash",
        },
        "council_cases": {
            "id",
            "session_id",
            "dossier_id",
            "dossier_version_id",
            "decision",
        },
        "council_votes": {
            "id",
            "case_id",
            "member_user_id",
            "choice",
            "reason",
            "voted_at",
        },
        "council_session_members": {
            "id",
            "session_id",
            "member_user_id",
            "attendance_confirmed_at",
        },
        "council_case_conflicts": {
            "id",
            "case_id",
            "member_user_id",
            "has_conflict",
            "reason",
            "declared_at",
        },
    }
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table, columns in expected_columns.items():
            assert table in tables
            actual = {
                row[1]
                for row in connection.execute(f"PRAGMA table_info({table})")
            }
            assert actual == columns

        session_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='council_sessions'"
        ).fetchone()
        vote_indexes = connection.execute(
            "PRAGMA index_list(council_votes)"
        ).fetchall()
        member_indexes = connection.execute(
            "PRAGMA index_list(council_session_members)"
        ).fetchall()
        conflict_indexes = connection.execute(
            "PRAGMA index_list(council_case_conflicts)"
        ).fetchall()

    assert session_sql is not None
    assert "quorum_required_positive" in session_sql[0]
    assert any(row[2] == 1 for row in vote_indexes)
    assert any(row[2] == 1 for row in member_indexes)
    assert any(row[2] == 1 for row in conflict_indexes)

    command.downgrade(config, "0009_reviews")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert not set(expected_columns).intersection(tables)
    assert "reviews" in tables
    get_settings.cache_clear()
