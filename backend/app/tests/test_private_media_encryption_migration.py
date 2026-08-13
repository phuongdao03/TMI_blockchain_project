import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_private_media_encryption_metadata_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "private-media-encryption.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0050_job_operations_permission")

    user_id = "1" * 32
    private_media_id = "2" * 32
    public_media_id = "3" * 32
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO users (id, email, password_hash, status) "
            "VALUES (?, ?, ?, ?)",
            (user_id, "legacy-encryption@tmigroup.vn", "unused", "ACTIVE"),
        )
        for media_id, public_id in (
            (private_media_id, "legacy/dossier-evidence/private-proof"),
            (public_media_id, "legacy/public-work/public-image"),
        ):
            connection.execute(
                "INSERT INTO media_assets ("
                "id, owner_user_id, cloudinary_public_id, cloudinary_version, "
                "resource_type, access_mode, original_filename, mime_type, bytes, "
                "sha256, status"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    media_id,
                    user_id,
                    public_id,
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

    command.upgrade(config, "0051_private_media_encryption")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
        private_row = connection.execute(
            "SELECT confidentiality, encryption_status, status "
            "FROM media_assets WHERE id = ?",
            (private_media_id,),
        ).fetchone()
        public_row = connection.execute(
            "SELECT confidentiality, encryption_status, status "
            "FROM media_assets WHERE id = ?",
            (public_media_id,),
        ).fetchone()
    assert {
        "confidentiality",
        "encryption_status",
        "encryption_algorithm",
        "encryption_key_id",
        "encryption_nonce",
        "encrypted_object_public_id",
        "encrypted_at",
    }.issubset(columns)
    assert private_row == ("PRIVATE", "LEGACY_UNENCRYPTED", "QUARANTINED")
    assert public_row == ("PUBLIC", "NOT_REQUIRED", "ACTIVE")

    command.downgrade(config, "0050_job_operations_permission")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
    assert "encryption_key_id" not in columns
    get_settings.cache_clear()
