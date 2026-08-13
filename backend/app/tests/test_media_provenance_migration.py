import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_provenance_migration_marks_legacy_hashes_for_reverification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "media-provenance.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0044_secure_media_inspection")

    user_id = "1" * 32
    media_id = "2" * 32
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO users (id, email, password_hash, status) "
            "VALUES (?, ?, ?, ?)",
            (user_id, "legacy@tmigroup.vn", "unused", "ACTIVE"),
        )
        connection.execute(
            "INSERT INTO media_assets ("
            "id, owner_user_id, cloudinary_public_id, cloudinary_version, "
            "resource_type, access_mode, original_filename, mime_type, bytes, "
            "sha256, status"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                media_id,
                user_id,
                "legacy/evidence",
                7,
                "raw",
                "authenticated",
                "legacy.pdf",
                "application/pdf",
                128,
                "a" * 64,
                "ACTIVE",
            ),
        )
        connection.commit()

    command.upgrade(config, "0045_trusted_media_provenance")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
        row = connection.execute(
            "SELECT hash_algorithm, hash_byte_length, inspection_policy_version, "
            "hash_storage_version, hash_computed_at "
            "FROM media_assets WHERE id = ?",
            (media_id,),
        ).fetchone()
        table_sql_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='media_assets'"
        ).fetchone()
        assert table_sql_row is not None

    assert {
        "hash_algorithm",
        "hash_byte_length",
        "inspection_policy_version",
        "hash_storage_version",
        "hash_computed_at",
    }.issubset(columns)
    assert row is not None
    assert row[:4] == ("SHA-256", 128, "legacy-unverified-v1", 7)
    assert row[4] is not None
    assert "hash_byte_length >= 0" in table_sql_row[0]

    command.downgrade(config, "0044_secure_media_inspection")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
    assert "hash_algorithm" not in columns
    get_settings.cache_clear()
