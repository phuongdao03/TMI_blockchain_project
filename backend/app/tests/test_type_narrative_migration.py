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


def test_type_narratives_preserve_old_catalog_and_guard_referenced_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "type-narratives.sqlite3"
    monkeypatch.setenv("DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{path.as_posix()}")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0150_dossier_applicant_claims")
        with sqlite3.connect(path) as connection:
            category = connection.execute(
                "SELECT category_id FROM dossier_types LIMIT 1"
            ).fetchone()[0]
            custom_id = uuid4().hex
            connection.execute(
                (
                    "INSERT INTO dossier_types (id, category_id, code, name) "
                    "VALUES (?, ?, 'CUSTOM_TEST', 'Custom type')"
                ),
                (custom_id, category),
            )
            connection.execute(
                (
                    "INSERT INTO dossier_type_versions (id, dossier_type_id, "
                    "version_no, schema_json) VALUES (?, ?, 1, ?)"
                ),
                (uuid4().hex, custom_id, json.dumps({"fields": []})),
            )
            old_rows = dict(
                connection.execute("SELECT id, schema_json FROM dossier_type_versions")
            )
            old_catalog = connection.execute(
                "SELECT id, code, name FROM dossier_types ORDER BY id"
            ).fetchall()
            latest = {
                code: json.loads(schema)
                for code, schema in connection.execute(
                    "SELECT t.code, v.schema_json FROM dossier_types t "
                    "JOIN dossier_type_versions v "
                    "ON v.dossier_type_id = t.id WHERE v.version_no = "
                    "(SELECT MAX(x.version_no) FROM "
                    "dossier_type_versions x WHERE x.dossier_type_id = "
                    "t.id)"
                )
            }
        command.upgrade(config, "0151_type_narrative_schemas")
        with sqlite3.connect(path) as connection:
            all_rows = dict(
                connection.execute("SELECT id, schema_json FROM dossier_type_versions")
            )
            assert all(all_rows[key] == value for key, value in old_rows.items())
            assert (
                connection.execute(
                    "SELECT id, code, name FROM dossier_types ORDER BY id"
                ).fetchall()
                == old_catalog
            )
            new_rows = connection.execute(
                "SELECT t.code, v.id, v.schema_json FROM dossier_type_versions v "
                "JOIN dossier_types t ON t.id = v.dossier_type_id"
            ).fetchall()
            new_rows = [
                (code, key, json.loads(raw))
                for code, key, raw in new_rows
                if key not in old_rows
            ]
            assert len(new_rows) == 12
            signatures = set()
            for code, _, schema in new_rows:
                assert code != "CUSTOM_TEST"
                validate_dynamic_schema(schema)
                previous = latest[code]
                assert {
                    key: value for key, value in schema.items() if key != "fields"
                } == {key: value for key, value in previous.items() if key != "fields"}
                original_fields = previous["fields"]
                assert schema["fields"][: len(original_fields)] == original_fields
                added = schema["fields"][len(original_fields) :]
                assert len(added) == 4
                assert all(
                    field["type"] == "textarea" and field["required"] is False
                    for field in added
                )
                assert all(
                    field["helpText"]
                    and field["placeholder"]
                    and field["maxLength"] == 5000
                    for field in added
                )
                assert not any(field.get("publicVisibility") for field in added)
                signatures.add(tuple(field["key"] for field in added))
            assert len(signatures) == 12
        command.downgrade(config, "0150_dossier_applicant_claims")
        with sqlite3.connect(path) as connection:
            assert (
                dict(
                    connection.execute(
                        "SELECT id, schema_json FROM dossier_type_versions"
                    )
                )
                == old_rows
            )
        command.upgrade(config, "0151_type_narrative_schemas")
        with sqlite3.connect(path) as connection:
            owner_id = uuid4().hex
            connection.execute(
                (
                    "INSERT INTO users (id, email, password_hash, status) "
                    "VALUES (?, 'narrative@example.test', 'test-only', "
                    "'ACTIVE')"
                ),
                (owner_id,),
            )
            version_id, type_id, category_id = connection.execute(
                "SELECT v.id, t.id, t.category_id FROM "
                "dossier_type_versions v JOIN dossier_types t "
                "ON t.id = v.dossier_type_id WHERE t.code = 'ARTWORK' "
                "ORDER BY v.version_no DESC LIMIT 1"
            ).fetchone()
            connection.execute(
                (
                    "INSERT INTO dossier_preparations (owner_user_id, "
                    "revision, payload_json) VALUES (?, 1, ?)"
                ),
                (owner_id, json.dumps({"dossierTypeVersionId": str(UUID(version_id))})),
            )
        with pytest.raises(RuntimeError, match="saved preparations"):
            command.downgrade(config, "0150_dossier_applicant_claims")
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
            command.downgrade(config, "0150_dossier_applicant_claims")
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM dossier_type_versions WHERE id = ?",
                    (version_id,),
                ).fetchone()[0]
                == 1
            )
            connection.execute(
                (
                    "UPDATE dossier_preparations SET payload_json = NULL "
                    "WHERE owner_user_id = ?"
                ),
                (owner_id,),
            )
            connection.execute(
                "INSERT INTO dossiers (id, code, owner_user_id, "
                "category_id, title, dossier_type_id, "
                "dossier_type_version_id) "
                "VALUES (?, 'NARRATIVE-MIGRATION-TEST', ?, ?, 'Preserved draft', ?, ?)",
                (uuid4().hex, owner_id, category_id, type_id, version_id),
            )
        with pytest.raises(RuntimeError, match="dossiers"):
            command.downgrade(config, "0150_dossier_applicant_claims")
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM dossiers WHERE dossier_type_version_id = ?",
                    (version_id,),
                ).fetchone()[0]
                == 1
            )
    finally:
        get_settings.cache_clear()
