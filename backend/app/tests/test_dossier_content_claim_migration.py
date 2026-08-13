import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_dossier_content_claim_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "dossier-content-claim-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0036_dossier_content_claims")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(dossier_content_claims)"
                )
            }
            assert columns == {
                "id",
                "content_fingerprint",
                "dossier_id",
                "dossier_version_id",
                "claimed_at",
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(dossier_content_claims)"
                )
            }
            assert "ix_dossier_content_claims_dossier_id" in indexes

        command.downgrade(config, "0035_engagement_velocity")
        with sqlite3.connect(database_path) as connection:
            assert (
                connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='dossier_content_claims'"
                ).fetchone()
                is None
            )
    finally:
        get_settings.cache_clear()
