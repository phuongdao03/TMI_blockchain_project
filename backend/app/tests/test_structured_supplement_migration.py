import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings


def test_supplement_migration_preserves_templates_and_refuses_history_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "supplements.sqlite3"
    monkeypatch.setenv("DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{path.as_posix()}")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(Path(__file__).resolve().parents[2] / "alembic.ini")
    try:
        command.upgrade(config, "0151_type_narrative_schemas")
        with sqlite3.connect(path) as db:
            original = db.execute(
                "SELECT id, schema_json FROM dossier_type_versions ORDER BY id"
            ).fetchall()
        command.upgrade(config, "0152_structured_supplements")
        command.downgrade(config, "0151_type_narrative_schemas")
        command.upgrade(config, "0152_structured_supplements")
        with sqlite3.connect(path) as db:
            assert (
                db.execute(
                    "SELECT id, schema_json FROM dossier_type_versions ORDER BY id"
                ).fetchall()
                == original
            )
            owner, dossier, version, request_id = (uuid4().hex for _ in range(4))
            category_id = db.execute("SELECT id FROM categories LIMIT 1").fetchone()[0]
            db.execute(
                (
                    "INSERT INTO users (id,email,password_hash,status) "
                    "VALUES (?, 'supplement-fixture@example.test', "
                    "'test-only', 'ACTIVE')"
                ),
                (owner,),
            )
            db.execute(
                (
                    "INSERT INTO dossiers "
                    "(id,code,owner_user_id,category_id,title) VALUES (?, "
                    "'SUPPLEMENT-TEST', ?, ?, 'Preserved dossier')"
                ),
                (dossier, owner, category_id),
            )
            db.execute(
                (
                    "INSERT INTO dossier_versions "
                    "(id,dossier_id,version_no,snapshot_json,canon"
                    "ical_hash,submitted_by) VALUES (?, ?, 1, ?, ?"
                    ", ?)"
                ),
                (version, dossier, json.dumps({"schemaVersion": 1}), "a" * 64, owner),
            )
            db.execute(
                (
                    "INSERT INTO supplement_requests "
                    "(id,dossier_id,requested_version_id,criterion"
                    "_key,criterion_label,requested_information,re"
                    "ason,priority,created_by,status,revision) VAL"
                    "UES (?, ?, ?, 'origin', 'Nguồn gốc', 'Supply "
                    "the dated source record.', 'The chronology ne"
                    "eds clarification.', 'NORMAL', ?, 'OPEN', 0)"
                ),
                (request_id, dossier, version, owner),
            )
        with pytest.raises(RuntimeError, match="history exists"):
            command.downgrade(config, "0151_type_narrative_schemas")
        with sqlite3.connect(path) as db:
            assert (
                db.execute("SELECT COUNT(*) FROM supplement_requests").fetchone()[0]
                == 1
            )
            assert (
                db.execute(
                    "SELECT title FROM dossiers WHERE id = ?", (dossier,)
                ).fetchone()[0]
                == "Preserved dossier"
            )
    finally:
        get_settings.cache_clear()
