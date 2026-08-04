import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_review_migration_upgrades_exact_schema_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "review-migration.sqlite3"
    direct_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_DIRECT_URL", direct_url)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0009_reviews")

    with sqlite3.connect(database_path) as connection:
        assignment_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(review_assignments)")
        }
        review_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(reviews)")
        }
        assignment_foreign_keys = {
            (row[2], row[3], row[6])
            for row in connection.execute("PRAGMA foreign_key_list(review_assignments)")
        }
        review_foreign_keys = {
            (row[2], row[3], row[6])
            for row in connection.execute("PRAGMA foreign_key_list(reviews)")
        }
        assignment_indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(review_assignments)")
        }
        review_indexes = connection.execute("PRAGMA index_list(reviews)").fetchall()
        assignment_sql = connection.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='review_assignments'
            """
        ).fetchone()
        review_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='reviews'"
        ).fetchone()

    assert assignment_columns == {
        "id",
        "dossier_id",
        "dossier_version_id",
        "reviewer_user_id",
        "assigned_by",
        "due_at",
        "status",
        "conflict_declared_at",
        "conflict_reason",
    }
    assert review_columns == {
        "id",
        "assignment_id",
        "truth_score",
        "transparency_score",
        "ownership_score",
        "professionalism_score",
        "respect_score",
        "total_score",
        "recommendation",
        "criterion_comments",
        "private_note",
        "submitted_at",
    }
    assert assignment_foreign_keys == {
        ("dossiers", "dossier_id", "RESTRICT"),
        ("dossier_versions", "dossier_version_id", "RESTRICT"),
        ("users", "reviewer_user_id", "RESTRICT"),
        ("users", "assigned_by", "RESTRICT"),
    }
    assert review_foreign_keys == {
        ("review_assignments", "assignment_id", "RESTRICT"),
    }
    assert "ix_review_assignments_reviewer_status_due_at" in assignment_indexes
    assert "uq_review_assignments_active_reviewer_version" in assignment_indexes
    assert any(row[2] == 1 for row in review_indexes)
    assert assignment_sql is not None
    assert "review_assignment_status" in assignment_sql[0]
    assert review_sql is not None
    assert "truth_score_range" in review_sql[0]
    assert "total_score_range" in review_sql[0]

    command.downgrade(config, "0008_dossier_evidences")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "review_assignments" not in tables
    assert "reviews" not in tables
    assert "dossier_evidences" in tables
    get_settings.cache_clear()
