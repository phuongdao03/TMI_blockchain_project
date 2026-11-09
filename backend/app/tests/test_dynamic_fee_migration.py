import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_dynamic_fee_migration_adds_policy_schema_without_seeding_fee(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "dynamic-fees.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"fee_policies", "fee_policy_events", "fee_waivers"}.issubset(tables)
        policy_count = connection.execute(
            "SELECT count(*) FROM fee_policies"
        ).fetchone()[0]
        assert policy_count == 0
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO fee_policies (
                id, fee_type, dossier_type_id, version_no, amount_minor,
                display_name, reason, starts_at, status, created_by_user_id
            ) VALUES (
                'draft-policy', 'DOSSIER_SUBMISSION', 'dossier-type', 1, 100,
                'Draft', 'Migration constraint check', '2030-01-01T00:00:00',
                'DRAFT', 'creator'
            )
            """
        )
        connection.execute(
            "UPDATE fee_policies SET status = 'CANCELLED' WHERE id = 'draft-policy'"
        )
        assert (
            connection.execute(
                "SELECT status FROM fee_policies WHERE id = 'draft-policy'"
            ).fetchone()[0]
            == "CANCELLED"
        )
        connection.execute("DELETE FROM fee_policies WHERE id = 'draft-policy'")
        dossier_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(dossiers)")
        }
        assert "submission_fee_policy_mode" in dossier_columns
        obligation_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(fee_obligations)")
        }
        assert {
            "fee_type",
            "fee_policy_id",
            "fee_policy_version_no",
            "gross_amount_minor",
            "waiver_amount_minor",
        }.issubset(obligation_columns)
        obligation_indexes = {
            row[1]: (row[2], row[4])
            for row in connection.execute("PRAGMA index_list(fee_obligations)")
        }
        assert obligation_indexes["uq_fee_obligations_dossier_fee_type"] == (1, 1)
        assert obligation_indexes["uq_fee_obligations_legacy_dossier_id"] == (1, 1)

    command.downgrade(config, "0159_media_upload_sessions")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert not {"fee_policies", "fee_policy_events", "fee_waivers"} & tables
        dossier_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(dossiers)")
        }
        assert "submission_fee_policy_mode" not in dossier_columns

    get_settings.cache_clear()
