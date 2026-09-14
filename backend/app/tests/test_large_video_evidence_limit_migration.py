import json
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
OLD_LIMIT = 100 * 1024 * 1024
NEW_LIMIT = 300 * 1024 * 1024


def _video_rule_limits(database_path: Path) -> list[int]:
    limits: list[int] = []
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT schema_json FROM dossier_type_versions"
        ).fetchall()
    for (raw_schema,) in rows:
        schema = json.loads(raw_schema) if isinstance(raw_schema, str) else raw_schema
        for rule in schema.get("documentRules", []):
            if {"video/mp4", "video/webm"}.intersection(
                rule.get("allowedMimeTypes", [])
            ):
                limits.append(rule["maxBytes"])
    return limits


def test_large_video_evidence_limit_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "large-video-evidence-limit.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0075_public_video_presentation")
    before = _video_rule_limits(database_path)
    assert before and OLD_LIMIT in before

    command.upgrade(config, "0076_large_video_evidence_limit")
    after = _video_rule_limits(database_path)
    assert after and OLD_LIMIT not in after
    assert NEW_LIMIT in after

    command.downgrade(config, "0075_public_video_presentation")
    restored = _video_rule_limits(database_path)
    assert restored == before
    get_settings.cache_clear()
