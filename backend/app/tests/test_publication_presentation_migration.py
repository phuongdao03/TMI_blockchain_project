import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings


def test_publication_presentation_migration_is_reversible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "presentation.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(Path(__file__).resolve().parents[2] / "alembic.ini")
    try:
        command.upgrade(config, "0077_publication_presentation")
        with sqlite3.connect(database) as connection:
            media = {
                row[1]
                for row in connection.execute("PRAGMA table_info(public_work_media)")
            }
            works = {
                row[1]: row
                for row in connection.execute("PRAGMA table_info(public_works)")
            }
            assert "poster_time_ms" in media
            assert works["show_certificate"][3] == 1
            assert works["show_certificate"][4] in ("1", "true")
        command.downgrade(config, "0076_large_video_evidence_limit")
        with sqlite3.connect(database) as connection:
            assert "poster_time_ms" not in {
                row[1]
                for row in connection.execute("PRAGMA table_info(public_work_media)")
            }
            assert "show_certificate" not in {
                row[1] for row in connection.execute("PRAGMA table_info(public_works)")
            }
    finally:
        get_settings.cache_clear()
