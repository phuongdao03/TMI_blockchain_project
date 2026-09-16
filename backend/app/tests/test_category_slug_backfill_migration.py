import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_category_slug_backfill_migration_repairs_legacy_categories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "category-slug-backfill.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0078_editorial_covers")
        with sqlite3.connect(database_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM categories WHERE slug IS NULL"
            ).fetchone() == (1,)

        command.upgrade(config, "0079_backfill_category_slugs")
        with sqlite3.connect(database_path) as connection:
            slugs = connection.execute(
                "SELECT slug FROM categories ORDER BY slug"
            ).fetchall()
        assert slugs
        assert all(slug and slug.strip() for (slug,) in slugs)
        assert len({slug for (slug,) in slugs}) == len(slugs)
    finally:
        get_settings.cache_clear()
