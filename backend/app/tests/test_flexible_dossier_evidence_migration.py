import json
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_flexible_evidence_catalog_creates_active_v3_schemas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "flexible-evidence.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0072_review_evidence_assessments")
    with sqlite3.connect(database_path) as connection:
        review_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(reviews)")
        }
        assert "evidence_assessments" in review_columns
        schemas = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT schema_json FROM dossier_type_versions WHERE version_no = 3"
            )
        ]
        assert len(schemas) == 12
        assert all(schema.get("reviewRubric") for schema in schemas)
        assert all(schema.get("documentRules") for schema in schemas)
        assert all(
            rule.get("required") is False
            for schema in schemas
            for rule in schema["documentRules"]
        )
        mime_types = {
            mime_type
            for schema in schemas
            for rule in schema["documentRules"]
            for mime_type in rule["allowedMimeTypes"]
        }
        assert "video/mp4" in mime_types
        assert "audio/mpeg" in mime_types
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in mime_types
        )

    command.downgrade(config, "0070_start_reviews_immediately")
    with sqlite3.connect(database_path) as connection:
        review_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(reviews)")
        }
        assert "evidence_assessments" not in review_columns
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM dossier_type_versions WHERE version_no = 3"
            ).fetchone()[0]
            == 0
        )
    get_settings.cache_clear()
