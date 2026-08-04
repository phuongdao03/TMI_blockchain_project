import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_public_work_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "public-work-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0014_public_catalog")

    with sqlite3.connect(database_path) as connection:
        assert _columns(connection, "public_works") == {
            "id",
            "dossier_id",
            "certificate_id",
            "owner_user_id",
            "organization_id",
            "slug",
            "title",
            "short_description",
            "full_description",
            "publication_status",
            "visibility",
            "author_display_name",
            "category_id",
            "thumbnail_media_id",
            "published_at",
            "scheduled_publish_at",
            "featured_at",
            "featured_until",
            "view_count",
            "version",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert _columns(connection, "public_work_slug_history") == {
            "id",
            "public_work_id",
            "slug",
            "created_at",
        }
        work_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='public_works'"
        ).fetchone()
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(public_works)")
        }
        foreign_keys = {
            (row[2], row[3], row[6])
            for row in connection.execute("PRAGMA foreign_key_list(public_works)")
        }

    assert work_sql is not None
    assert "ck_public_works_publication_status" in work_sql[0]
    assert "ck_public_works_public_work_visibility" in work_sql[0]
    assert "ck_public_works_view_count_non_negative" in work_sql[0]
    assert "ck_public_works_version_positive" in work_sql[0]
    assert {
        "ix_public_works_status_visibility_published",
        "ix_public_works_category_status_visibility",
    }.issubset(indexes)
    assert foreign_keys == {
        ("dossiers", "dossier_id", "RESTRICT"),
        ("certificates", "certificate_id", "RESTRICT"),
        ("users", "owner_user_id", "RESTRICT"),
        ("organizations", "organization_id", "RESTRICT"),
        ("categories", "category_id", "RESTRICT"),
        ("media_assets", "thumbnail_media_id", "RESTRICT"),
    }

    command.downgrade(config, "0013_operations")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "public_works" not in tables
    assert "public_work_slug_history" not in tables
    get_settings.cache_clear()


def test_public_work_migration_enforces_one_projection_per_dossier_and_slug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "public-work-constraints.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0014_public_catalog")

    with sqlite3.connect(database_path) as connection:
        indexes = connection.execute("PRAGMA index_list(public_works)").fetchall()
        unique_columns = {
            tuple(
                item[2] for item in connection.execute(f'PRAGMA index_info("{row[1]}")')
            )
            for row in indexes
            if row[2] == 1
        }
        slug_indexes = connection.execute(
            "PRAGMA index_list(public_work_slug_history)"
        ).fetchall()

    assert ("dossier_id",) in unique_columns
    assert ("slug",) in unique_columns
    assert any(row[2] == 1 for row in slug_indexes)
    get_settings.cache_clear()
