import json
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings
from app.modules.dossiers.dynamic_schema import validate_dynamic_schema

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_evidence_policy_versions_preserve_catalog_and_old_schemas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "evidence-policy.sqlite3"
    monkeypatch.setenv("DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{path.as_posix()}")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0148_promotion_distribution_media")
        with sqlite3.connect(path) as connection:
            old = connection.execute(
                "SELECT id, schema_json FROM dossier_type_versions ORDER BY id"
            ).fetchall()
            catalog = connection.execute(
                "SELECT id, code, name FROM dossier_types ORDER BY id"
            ).fetchall()
        command.upgrade(config, "0149_review_evidence_policy")
        with sqlite3.connect(path) as connection:
            after = dict(
                connection.execute("SELECT id, schema_json FROM dossier_type_versions")
            )
            assert all(after[key] == schema for key, schema in old)
            assert (
                connection.execute(
                    "SELECT id, code, name FROM dossier_types ORDER BY id"
                ).fetchall()
                == catalog
            )
            new_schemas = [
                json.loads(value)
                for key, value in after.items()
                if key not in dict(old)
            ]
            assert len(new_schemas) == 12
            for schema in new_schemas:
                validate_dynamic_schema(schema)
                assert schema["reviewRubric"]["evidencePolicyVersion"] == "2026.1"
                assert all(
                    c["verificationRequired"] is False
                    for c in schema["reviewRubric"]["criteria"]
                )
        command.downgrade(config, "0148_promotion_distribution_media")
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute(
                    "SELECT id, schema_json FROM dossier_type_versions ORDER BY id"
                ).fetchall()
                == old
            )
        command.upgrade(config, "0149_review_evidence_policy")
        with sqlite3.connect(path) as connection:
            owner_id = uuid4().hex
            dossier_id = uuid4().hex
            connection.execute(
                "INSERT INTO users (id, email, password_hash, status) "
                "VALUES (?, ?, 'test-only', 'ACTIVE')",
                (owner_id, "migration-fixture@example.test"),
            )
            version_id, type_id, category_id = connection.execute(
                "SELECT v.id, t.id, t.category_id FROM dossier_type_versions v "
                "JOIN dossier_types t ON t.id = v.dossier_type_id "
                "ORDER BY v.version_no DESC LIMIT 1"
            ).fetchone()
            connection.execute(
                "INSERT INTO dossier_preparations "
                "(owner_user_id, revision, payload_json) "
                "VALUES (?, 1, ?)",
                (owner_id, json.dumps({"dossierTypeVersionId": str(UUID(version_id))})),
            )
        with pytest.raises(RuntimeError, match="saved preparations"):
            command.downgrade(config, "0148_promotion_distribution_media")
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE dossier_preparations SET payload_json = ? "
                "WHERE owner_user_id = ?",
                (
                    json.dumps({"dossierTypeVersionId": UUID(version_id).hex.upper()}),
                    owner_id,
                ),
            )
        with pytest.raises(RuntimeError, match="saved preparations"):
            command.downgrade(config, "0148_promotion_distribution_media")
        with sqlite3.connect(path) as connection:
            connection.execute(
                "UPDATE dossier_preparations SET payload_json = NULL "
                "WHERE owner_user_id = ?",
                (owner_id,),
            )
            connection.execute(
                "INSERT INTO dossiers (id, code, owner_user_id, category_id, title, "
                "dossier_type_id, dossier_type_version_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    dossier_id,
                    "MIGRATION-TEST",
                    owner_id,
                    category_id,
                    "Preserved draft",
                    type_id,
                    version_id,
                ),
            )
        with pytest.raises(RuntimeError, match="in use"):
            command.downgrade(config, "0148_promotion_distribution_media")
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute(
                    "SELECT dossier_type_version_id FROM dossiers WHERE id = ?",
                    (dossier_id,),
                ).fetchone()[0]
                == version_id
            )
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM dossier_type_versions WHERE id = ?",
                    (version_id,),
                ).fetchone()[0]
                == 1
            )
    finally:
        get_settings.cache_clear()
