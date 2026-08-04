import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / "0018_search_foundation.py"
SEARCH_COLUMNS = {
    "search_organization_text",
    "search_taxonomy_text",
    "search_certificate_text",
    "search_vector",
}
SEARCH_INDEXES = {
    "ix_public_works_search_vector_public",
    "ix_public_works_title_trgm_public",
    "ix_public_works_author_trgm_public",
    "ix_public_works_search_visibility_published_id",
}


def test_search_foundation_upgrade_backfill_and_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "search-foundation.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0017_content_reports")
    work_id = uuid4().hex
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO public_works (
              id, dossier_id, owner_user_id, slug, title, short_description,
              full_description, author_display_name, category_id,
              publication_status, visibility
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_id,
                uuid4().hex,
                uuid4().hex,
                "searchable-work",
                "Di sản số Việt Nam",
                "Mô tả công khai",
                "Nội dung dài",
                "TMI Studio",
                uuid4().hex,
                "PUBLISHED",
                "PUBLIC",
            ),
        )
        connection.commit()

    command.upgrade(config, "0018_search_foundation")
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(public_works)")
        }
        indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(public_works)")
        }
        row = connection.execute(
            """
            SELECT search_vector, publication_status, visibility
            FROM public_works WHERE id = ?
            """,
            (work_id,),
        ).fetchone()
    assert SEARCH_COLUMNS.issubset(columns)
    assert SEARCH_INDEXES.issubset(indexes)
    assert row is not None
    assert "Di sản số Việt Nam" in row[0]
    assert row[1:] == ("PUBLISHED", "PUBLIC")

    command.downgrade(config, "0017_content_reports")
    with sqlite3.connect(database_path) as connection:
        downgraded_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(public_works)")
        }
        downgraded_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(public_works)")
        }
    assert SEARCH_COLUMNS.isdisjoint(downgraded_columns)
    assert SEARCH_INDEXES.isdisjoint(downgraded_indexes)
    get_settings.cache_clear()


def test_postgresql_search_contract_is_weighted_partial_and_operational() -> None:
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    for required in (
        "CREATE EXTENSION IF NOT EXISTS unaccent",
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
        "setweight",
        "'A'",
        "'B'",
        "'C'",
        "gin_trgm_ops",
        'postgresql_using="gin"',
        "postgresql_concurrently=True",
        "FOR UPDATE SKIP LOCKED",
        "publication_status = 'PUBLISHED'",
        "visibility = 'PUBLIC'",
        "deleted_at IS NULL",
    ):
        assert required in source
    assert "DROP EXTENSION" not in source
