import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_media_asset_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "media-asset-migration.sqlite3"
    direct_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_DIRECT_URL", direct_url)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0006_media_assets")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(media_assets)")
        }
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(media_assets)")
        }
        media_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(media_assets)"
        ).fetchall()
        profile_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(user_profiles)"
        ).fetchall()
        table_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='media_assets'"
        ).fetchone()
        assert table_row is not None
        table_sql = table_row[0]

    assert columns == {
        "id",
        "owner_user_id",
        "cloudinary_public_id",
        "cloudinary_version",
        "resource_type",
        "access_mode",
        "original_filename",
        "mime_type",
        "bytes",
        "width",
        "height",
        "duration_ms",
        "sha256",
        "status",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert {
        "ix_media_assets_owner_status_created_at",
        "ix_media_assets_status_created_at",
        "sqlite_autoindex_media_assets_2",
    }.issubset(indexes)
    assert any(
        row[2] == "users" and row[3] == "owner_user_id" and row[6] == "RESTRICT"
        for row in media_foreign_keys
    )
    assert any(
        row[2] == "media_assets"
        and row[3] == "avatar_media_id"
        and row[6] == "SET NULL"
        for row in profile_foreign_keys
    )
    for constraint_name in (
        "ck_media_assets_bytes_non_negative",
        "ck_media_assets_cloudinary_version_non_negative",
        "ck_media_assets_width_non_negative",
        "ck_media_assets_height_non_negative",
        "ck_media_assets_duration_ms_non_negative",
        "ck_media_assets_media_status",
    ):
        assert constraint_name in table_sql

    command.downgrade(config, "0005_organizations")

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        profile_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(user_profiles)"
        ).fetchall()

    assert "media_assets" not in tables
    assert not any(
        row[2] == "media_assets" and row[3] == "avatar_media_id"
        for row in profile_foreign_keys
    )
    get_settings.cache_clear()
