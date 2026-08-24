import json
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_certificate_version_qr_migration_backfills_only_current_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "certificate-version-qr.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    certificate_id = "10000000000040008000000000000001"
    current_version_id = "20000000000040008000000000000001"
    historic_version_id = "20000000000040008000000000000002"
    dossier_id = "30000000000040008000000000000001"
    token_hash = "a" * 64
    qr_payload = "https://verify.example.test/verify/current-version-token"

    command.upgrade(config, "0059_document_rule_visibility")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO certificates ("
            "id, certificate_number, dossier_id, current_version_no, status, "
            "issued_at, public_token_hash, qr_payload"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                certificate_id,
                "THV-2026-QR-MIGRATION",
                dossier_id,
                1,
                "ACTIVE",
                "2026-08-24 00:00:00",
                token_hash,
                qr_payload,
            ),
        )
        connection.execute(
            "INSERT INTO certificate_versions ("
            "id, certificate_id, version_no, dossier_version_id, metadata_json, "
            "metadata_hash, status"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                current_version_id,
                certificate_id,
                1,
                dossier_id,
                json.dumps({"certificateVersion": 1}),
                "b" * 64,
                "ACTIVE",
            ),
        )
        connection.execute(
            "INSERT INTO certificate_versions ("
            "id, certificate_id, version_no, predecessor_version_id, "
            "dossier_version_id, metadata_json, metadata_hash, status, change_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                historic_version_id,
                certificate_id,
                2,
                current_version_id,
                dossier_id,
                json.dumps({"certificateVersion": 2}),
                "c" * 64,
                "SUPERSEDED",
                "Imported historic version without a distinct QR token.",
            ),
        )
        connection.commit()

    command.upgrade(config, "0060_certificate_version_qr")
    with sqlite3.connect(database_path) as connection:
        assert {"public_token_hash", "qr_payload"}.issubset(
            _columns(connection, "certificate_versions")
        )
        assert connection.execute(
            "SELECT public_token_hash, qr_payload FROM certificate_versions "
            "WHERE id = ?",
            (current_version_id,),
        ).fetchone() == (token_hash, qr_payload)
        assert connection.execute(
            "SELECT public_token_hash, qr_payload FROM certificate_versions "
            "WHERE id = ?",
            (historic_version_id,),
        ).fetchone() == (None, None)

    command.downgrade(config, "0059_document_rule_visibility")
    with sqlite3.connect(database_path) as connection:
        assert {"public_token_hash", "qr_payload"}.isdisjoint(
            _columns(connection, "certificate_versions")
        )
    get_settings.cache_clear()
