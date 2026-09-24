import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_work_allocation_schema_and_review_bridge_are_additive_and_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "work-allocations.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0093_allocation_review")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            allocation_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list('work_allocations')")
            }
            member_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list('allocation_members')")
            }
            scope_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' "
                "AND name = 'work_scopes'"
            ).fetchone()[0]
            member_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' "
                "AND name = 'allocation_members'"
            ).fetchone()[0]
            bridge_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list('work_scope_review_assignments')"
                )
            }

        assert {
            "work_allocations",
            "work_scopes",
            "allocation_members",
            "work_scope_review_assignments",
            "tasks",
            "review_assignments",
        }.issubset(tables)
        assert "ix_work_allocations_dossier_version_status" in allocation_indexes
        assert "ix_allocation_members_user_active" in member_indexes
        assert {
            "ix_work_scope_review_assignments_scope",
            "ix_work_scope_review_assignments_review_assignment",
        }.issubset(bridge_indexes)
        assert all(
            name in scope_schema for name in ("work_scope_type", "work_scope_source")
        )
        assert all(
            name in member_schema
            for name in (
                "allocation_responsibility",
                "allocation_member_active_lifecycle",
            )
        )

        command.downgrade(config, "0091_location_retention")
        with sqlite3.connect(database_path) as connection:
            tables_after_downgrade = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        assert "work_allocations" not in tables_after_downgrade
        assert "work_scopes" not in tables_after_downgrade
        assert "allocation_members" not in tables_after_downgrade
        assert "work_scope_review_assignments" not in tables_after_downgrade
        assert {"tasks", "review_assignments"}.issubset(tables_after_downgrade)
    finally:
        get_settings.cache_clear()
