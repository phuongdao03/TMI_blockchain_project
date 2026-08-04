import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_category_ranking_migration_backfills_and_round_trips(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "category-ranking-migration.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0026_ranking_snapshots")

    category_a, category_b = uuid4(), uuid4()
    snapshot_id = uuid4()
    works = [(uuid4(), category_a, 10), (uuid4(), category_b, 9)]
    works.extend([(uuid4(), category_a, 8), (uuid4(), category_a, 8)])
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO categories (id, code, name) VALUES (?, ?, ?)",
            (
                (category_a.hex, "CATEGORY_A", "Category A"),
                (category_b.hex, "CATEGORY_B", "Category B"),
            ),
        )
        connection.executemany(
            """
            INSERT INTO public_works
                (id, dossier_id, owner_user_id, slug, title,
                 short_description, category_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    work_id.hex,
                    uuid4().hex,
                    uuid4().hex,
                    f"work-{position}",
                    f"Work {position}",
                    "Description",
                    category_id.hex,
                )
                for position, (work_id, category_id, _) in enumerate(works)
            ),
        )
        connection.execute(
            """
            INSERT INTO ranking_snapshots
                (id, campaign_id, version, formula_version,
                 campaign_rule_version, source_digest, result_digest,
                 candidate_count, total_valid_votes)
            VALUES (?, ?, 1, 'effective-votes-v1', 1, ?, ?, 4, 35)
            """,
            (snapshot_id.hex, uuid4().hex, "a" * 64, "b" * 64),
        )
        connection.executemany(
            """
            INSERT INTO ranking_snapshot_items
                (snapshot_id, work_id, rank, display_order, score,
                 effective_vote_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (snapshot_id.hex, work_id.hex, position, position, score, score)
                for position, (work_id, _, score) in enumerate(works, start=1)
            ),
        )

    command.upgrade(config, "0027_category_ranking")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]: row[3]
            for row in connection.execute("PRAGMA table_info(ranking_snapshot_items)")
        }
        indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(ranking_snapshot_items)")
        }
        foreign_keys = {
            (row[3], row[2], row[4], row[6])
            for row in connection.execute(
                "PRAGMA foreign_key_list(ranking_snapshot_items)"
            )
        }
        table_sql = connection.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'table' AND name = 'ranking_snapshot_items'
            """
        ).fetchone()[0]
        rows = connection.execute(
            """
            SELECT work_id, category_id, category_rank
            FROM ranking_snapshot_items
            ORDER BY display_order
            """
        ).fetchall()

    assert columns["category_id"] == 1
    assert columns["category_rank"] == 1
    assert "ix_ranking_snapshot_items_category_rank" in indexes
    assert ("category_id", "categories", "id", "RESTRICT") in foreign_keys
    assert "category_rank > 0" in table_sql
    assert rows == [
        (works[0][0].hex, category_a.hex, 1),
        (works[1][0].hex, category_b.hex, 1),
        (works[2][0].hex, category_a.hex, 2),
        (works[3][0].hex, category_a.hex, 2),
    ]

    command.downgrade(config, "0026_ranking_snapshots")
    with sqlite3.connect(database_path) as connection:
        columns_after_downgrade = {
            row[1]
            for row in connection.execute("PRAGMA table_info(ranking_snapshot_items)")
        }
    assert "category_id" not in columns_after_downgrade
    assert "category_rank" not in columns_after_downgrade
    get_settings.cache_clear()
