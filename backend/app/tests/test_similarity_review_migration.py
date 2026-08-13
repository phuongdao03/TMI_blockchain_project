import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_similarity_review_schema_and_permission_are_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "similarity-review.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0046_similarity_review_cases")
    with sqlite3.connect(database_path) as connection:
        media_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(similarity_review_cases)")
        }
        permission = connection.execute(
            "SELECT r.code, p.code FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE p.code = 'similarity.review'"
        ).fetchall()

    assert "perceptual_hash" in media_columns
    assert {
        "left_dossier_version_id",
        "right_dossier_version_id",
        "signal_type",
        "text_score",
        "image_distance",
        "policy_version",
        "status",
        "assigned_reviewer_user_id",
        "disposition",
        "resolution_reason",
    }.issubset(columns)
    assert permission == [("REVIEWER", "similarity.review")]

    command.downgrade(config, "0045_trusted_media_provenance")
    with sqlite3.connect(database_path) as connection:
        media_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
        assert "perceptual_hash" not in media_columns
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='similarity_review_cases'"
            ).fetchone()
            is None
        )
        assert connection.execute(
            "SELECT count(*) FROM permissions WHERE code = 'similarity.review'"
        ).fetchone() == (0,)
    get_settings.cache_clear()
