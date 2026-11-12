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
        policy_columns = {
            row[1]: row for row in connection.execute("PRAGMA table_info(fee_policies)")
        }
        assert policy_columns["dossier_type_id"][3] == 0
        version_columns = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info(dossier_versions)")
        }
        assert version_columns["submitted_at"][3] == 0
        for table, column in (
            ("users", "is_test_account"),
            ("staff_invitations", "is_test_account"),
            ("dossiers", "is_test"),
            ("fee_obligations", "is_test"),
            ("payment_orders", "is_test"),
        ):
            columns = {
                row[1] for row in connection.execute(f"PRAGMA table_info({table})")
            }
            assert column in columns
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
        connection.execute(
            """
            INSERT INTO fee_policies (
                id, fee_type, dossier_type_id, version_no, amount_minor,
                display_name, reason, starts_at, status, created_by_user_id
            ) VALUES (
                'global-policy', 'DOSSIER_SUBMISSION', NULL, 1, 5000000,
                'Global', 'Global policy migration check', '2030-01-01T00:00:00',
                'DRAFT', 'creator'
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO fee_policies (
                    id, fee_type, dossier_type_id, version_no, amount_minor,
                    display_name, reason, starts_at, status, created_by_user_id
                ) VALUES (
                    'global-policy-duplicate', 'DOSSIER_SUBMISSION', NULL, 1,
                    6000000, 'Duplicate', 'Global duplicate check',
                    '2031-01-01T00:00:00', 'DRAFT', 'creator'
                )
                """
            )
        connection.execute("DELETE FROM fee_policies WHERE id = 'global-policy'")
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


def test_test_marker_migration_refuses_downgrade_after_account_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "test-marker-downgrade.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO users (id, email, status, is_test_account) "
            "VALUES ('test-user', 'tester@example.test', 'ACTIVE', 1)"
        )

    with pytest.raises(RuntimeError, match="TEST account data"):
        command.downgrade(config, "0162_pending_submission_snapshots")

    get_settings.cache_clear()


def test_global_fee_migration_refuses_downgrade_with_global_policy_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "global-fee-downgrade.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "head")
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO fee_policies (
                id, fee_type, dossier_type_id, version_no, amount_minor,
                display_name, reason, starts_at, status, created_by_user_id
            ) VALUES (
                'global-policy', 'DOSSIER_SUBMISSION', NULL, 1, 5000000,
                'Global', 'Global policy migration check', '2030-01-01T00:00:00',
                'DRAFT', 'creator'
            )
            """
        )

    with pytest.raises(RuntimeError, match="global fee policies"):
        command.downgrade(config, "0160_dynamic_dossier_fees")

    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM fee_policies WHERE dossier_type_id IS NULL"
            ).fetchone()[0]
            == 1
        )
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
        assert revision == "0161_global_dossier_submission_fee"

    get_settings.cache_clear()
