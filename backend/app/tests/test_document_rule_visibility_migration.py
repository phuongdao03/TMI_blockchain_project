import json
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_document_rule_visibility_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "document-rule-visibility.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0059_document_rule_visibility")
    with sqlite3.connect(database_path) as connection:
        schemas = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT schema_json FROM dossier_type_versions WHERE version_no = 2"
            )
        ]
        assert len(schemas) == 12
        assert all(schema.get("documentRules") for schema in schemas)
        assert {
            rule["defaultVisibility"]
            for schema in schemas
            for rule in schema["documentRules"]
        } >= {"INTERNAL", "PUBLIC_PREVIEW"}
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' "
            "AND name = 'dossier_evidences'"
        ).fetchone()
        assert table_sql is not None
        assert "PUBLIC_PREVIEW" in table_sql[0]

    command.downgrade(config, "0058_four_product_roles")
    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM dossier_type_versions").fetchone()[
                0
            ]
            == 12
        )
    get_settings.cache_clear()
