import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_dynamic_dossier_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "dynamic-dossier.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0054_dynamic_dossier_types")

    with sqlite3.connect(database_path) as connection:
        assert {"dossier_types", "dossier_type_versions"}.issubset(
            {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        )
        dossier_columns = _columns(connection, "dossiers")
        assert {
            "dossier_type_id",
            "dossier_type_version_id",
            "form_data_json",
        }.issubset(dossier_columns)
        assert {"evidence_role", "access_scope"}.issubset(
            _columns(connection, "dossier_evidences")
        )
        assert {"is_primary"}.issubset(_columns(connection, "review_assignments"))
        assert {"checklist_answers", "applicant_feedback"}.issubset(
            _columns(connection, "reviews")
        )

    command.downgrade(config, "0053_document_chain_evidence")

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"dossier_types", "dossier_type_versions"}.isdisjoint(tables)
    get_settings.cache_clear()
