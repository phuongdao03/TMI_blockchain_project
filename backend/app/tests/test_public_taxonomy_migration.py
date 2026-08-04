import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_public_taxonomy_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "taxonomy.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0015_public_taxonomy")

    with sqlite3.connect(database_path) as connection:
        category_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(categories)")
        }
        tag_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(public_tags)")
        }
        join_pk = {
            row[1]
            for row in connection.execute("PRAGMA table_info(public_work_tags)")
            if row[5] > 0
        }
    assert {"parent_id", "slug"}.issubset(category_columns)
    assert tag_columns == {
        "id",
        "name",
        "slug",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert join_pk == {"public_work_id", "tag_id"}

    command.downgrade(config, "0014_public_catalog")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        category_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(categories)")
        }
    assert "public_tags" not in tables
    assert "public_work_tags" not in tables
    assert "parent_id" not in category_columns
    assert "slug" not in category_columns
    get_settings.cache_clear()
