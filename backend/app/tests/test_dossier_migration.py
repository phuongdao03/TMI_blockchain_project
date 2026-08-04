import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_dossier_migration_upgrades_seeds_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "dossier-migration.sqlite3"
    direct_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_DIRECT_URL", direct_url)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0007_dossiers")

    with sqlite3.connect(database_path) as connection:
        assert _columns(connection, "categories") == {
            "id",
            "code",
            "name",
            "description",
            "is_active",
            "display_order",
        }
        assert _columns(connection, "dossiers") == {
            "id",
            "code",
            "owner_user_id",
            "organization_id",
            "category_id",
            "title",
            "slug",
            "summary",
            "status",
            "visibility",
            "current_version_no",
            "submitted_at",
            "approved_at",
            "published_at",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert _columns(connection, "dossier_versions") == {
            "id",
            "dossier_id",
            "version_no",
            "snapshot_json",
            "canonical_hash",
            "submitted_by",
            "submitted_at",
        }
        assert _columns(connection, "dossier_status_history") == {
            "id",
            "dossier_id",
            "from_status",
            "to_status",
            "actor_user_id",
            "reason_code",
            "note",
            "created_at",
        }
        seed = connection.execute(
            """
            SELECT code, name, is_active, display_order
            FROM categories
            """
        ).fetchall()
        dossier_table = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='dossiers'"
        ).fetchone()
        version_table = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type='table' AND name='dossier_versions'
            """
        ).fetchone()
        dossier_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(dossiers)"
        ).fetchall()
        version_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(dossier_versions)"
        ).fetchall()
        history_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(dossier_status_history)"
        ).fetchall()
        dossier_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(dossiers)")
        }
        history_indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(dossier_status_history)")
        }
        assert dossier_table is not None
        assert version_table is not None

    assert seed == [("DIGITAL_INTELLECTUAL_ASSET", "Tài sản trí tuệ số", 1, 0)]
    for constraint_name in (
        "ck_dossiers_dossier_status",
        "ck_dossiers_visibility",
        "ck_dossiers_current_version_no_non_negative",
    ):
        assert constraint_name in dossier_table[0]
    for constraint_name in (
        "uq_dossier_versions_dossier_id_version_no",
        "ck_dossier_versions_version_no_positive",
    ):
        assert constraint_name in version_table[0]
    assert {
        "ix_dossiers_owner_status_created_at",
        "ix_dossiers_organization_status",
    }.issubset(dossier_indexes)
    assert "ix_dossier_status_history_dossier_created_at" in history_indexes
    assert {(row[2], row[3], row[6]) for row in dossier_foreign_keys} == {
        ("users", "owner_user_id", "RESTRICT"),
        ("organizations", "organization_id", "RESTRICT"),
        ("categories", "category_id", "RESTRICT"),
    }
    assert {(row[2], row[3], row[6]) for row in version_foreign_keys} == {
        ("dossiers", "dossier_id", "CASCADE"),
        ("users", "submitted_by", "RESTRICT"),
    }
    assert {(row[2], row[3], row[6]) for row in history_foreign_keys} == {
        ("dossiers", "dossier_id", "CASCADE"),
        ("users", "actor_user_id", "RESTRICT"),
    }

    command.downgrade(config, "0006_media_assets")

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {
        "categories",
        "dossiers",
        "dossier_versions",
        "dossier_status_history",
    }.isdisjoint(tables)
    assert "media_assets" in tables
    get_settings.cache_clear()
