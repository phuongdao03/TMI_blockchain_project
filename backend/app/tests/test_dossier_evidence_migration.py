import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_dossier_evidence_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "dossier-evidence-migration.sqlite3"
    direct_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_DIRECT_URL", direct_url)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0008_dossier_evidences")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(dossier_evidences)")
        }
        nullable = {
            row[1]: not bool(row[3])
            for row in connection.execute("PRAGMA table_info(dossier_evidences)")
        }
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(dossier_evidences)"
        ).fetchall()
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(dossier_evidences)")
        }
        table_row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type='table' AND name='dossier_evidences'
            """
        ).fetchone()

    assert columns == {
        "id",
        "dossier_id",
        "dossier_version_id",
        "media_asset_id",
        "evidence_type",
        "title",
        "description",
        "issued_at",
        "display_order",
        "is_public",
    }
    assert nullable["dossier_id"] is False
    assert nullable["dossier_version_id"] is True
    assert {(row[2], row[3], row[6]) for row in foreign_keys} == {
        ("dossiers", "dossier_id", "CASCADE"),
        ("dossier_versions", "dossier_version_id", "RESTRICT"),
        ("media_assets", "media_asset_id", "RESTRICT"),
    }
    assert "ix_dossier_evidences_dossier_version_order" in indexes
    assert table_row is not None
    assert "ck_dossier_evidences_display_order_non_negative" in table_row[0]

    command.downgrade(config, "0007_dossiers")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "dossier_evidences" not in tables
    assert "dossiers" in tables
    get_settings.cache_clear()
