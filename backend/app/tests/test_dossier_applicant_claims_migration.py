import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings


def test_claim_columns_preserve_old_dossier_and_refuse_destructive_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "claims.sqlite3"
    monkeypatch.setenv("DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{path.as_posix()}")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(Path(__file__).resolve().parents[2] / "alembic.ini")
    try:
        command.upgrade(config, "0149_review_evidence_policy")
        owner_id, dossier_id = uuid4().hex, uuid4().hex
        with sqlite3.connect(path) as connection:
            connection.execute(
                "INSERT INTO users (id,email,password_hash,status) "
                "VALUES (?, 'claims@example.test', 'unused', 'ACTIVE')",
                (owner_id,),
            )
            category_id = connection.execute(
                "SELECT id FROM categories LIMIT 1"
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO dossiers (id,code,owner_user_id,category_id,title) "
                "VALUES (?, 'OLD-CLAIM-TEST', ?, ?, 'Old dossier')",
                (dossier_id, owner_id, category_id),
            )
        command.upgrade(config, "0150_dossier_applicant_claims")
        with sqlite3.connect(path) as connection:
            assert connection.execute(
                "SELECT title,claims_json,claims_revision FROM dossiers WHERE id=?",
                (dossier_id,),
            ).fetchone() == ("Old dossier", "[]", 0)
        command.downgrade(config, "0149_review_evidence_policy")
        command.upgrade(config, "0150_dossier_applicant_claims")
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE dossiers SET claims_revision=1 WHERE id=?", (dossier_id,)
            )
        with pytest.raises(RuntimeError, match="edited"):
            command.downgrade(config, "0149_review_evidence_policy")
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute(
                    "SELECT title FROM dossiers WHERE id=?", (dossier_id,)
                ).fetchone()[0]
                == "Old dossier"
            )
    finally:
        get_settings.cache_clear()
