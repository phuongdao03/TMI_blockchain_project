import json
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_verdict_review_migration_is_reversible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "verdict-review.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0073_verdict_based_reviews")
    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(reviews)")}
        assert "criterion_verdicts" in columns
        schema_json = connection.execute(
            "SELECT schema_json FROM dossier_type_versions "
            "ORDER BY version_no DESC LIMIT 1"
        ).fetchone()[0]
        assert json.loads(schema_json)["reviewRubric"]["assessmentMethod"] == "VERDICT"

    command.downgrade(config, "0072_review_evidence_assessments")
    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(reviews)")}
        assert "criterion_verdicts" not in columns
    get_settings.cache_clear()
