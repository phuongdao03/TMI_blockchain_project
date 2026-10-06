import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_existing_dossier_types_are_available_as_public_work_categories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "public-work-categories.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0096_attendance_worked_duration")
        with sqlite3.connect(database_path) as connection:
            original = connection.execute(
                "SELECT id FROM categories WHERE code = 'DIGITAL_INTELLECTUAL_ASSET'"
            ).fetchone()
            assert connection.execute("SELECT COUNT(*) FROM categories").fetchone() == (
                1,
            )

        command.upgrade(config, "0097_seed_public_work_categories")
        with sqlite3.connect(database_path) as connection:
            codes = {
                code
                for (code,) in connection.execute(
                    "SELECT code FROM categories "
                    "WHERE is_active = 1 AND slug IS NOT NULL"
                )
            }
            assert len(codes) == 12
            assert {"CULTURAL_HERITAGE", "ARTWORK", "TRADEMARK"} <= codes
            assert (
                connection.execute(
                    "SELECT id FROM categories "
                    "WHERE code = 'DIGITAL_INTELLECTUAL_ASSET'"
                ).fetchone()
                == original
            )
    finally:
        get_settings.cache_clear()
