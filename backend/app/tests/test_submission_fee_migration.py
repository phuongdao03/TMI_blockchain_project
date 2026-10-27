import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_fee_migration_keeps_legacy_rows_and_blocks_unsafe_downgrade() -> None:
    filename = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/0143_submission_fee_policy.py"
    )
    spec = importlib.util.spec_from_file_location("submission_fee_migration", filename)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            sa.text("CREATE TABLE dossiers (id TEXT PRIMARY KEY, status TEXT NOT NULL)")
        )
        connection.execute(
            sa.text(
                "INSERT INTO dossiers VALUES ('legacy-paid', 'PAID'), "
                "('legacy-draft', 'DRAFT')"
            )
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            rows = connection.execute(
                sa.text(
                    "SELECT id, status, submission_fee_required "
                    "FROM dossiers ORDER BY id"
                )
            ).all()
            assert rows == [("legacy-draft", "DRAFT", 0), ("legacy-paid", "PAID", 0)]
            connection.execute(
                sa.text(
                    "INSERT INTO dossiers (id, status, submission_fee_required) "
                    "VALUES ('new', 'PAYMENT_PENDING', true)"
                )
            )
            with pytest.raises(RuntimeError, match="new-policy dossiers"):
                migration.downgrade()
            connection.execute(sa.text("DELETE FROM dossiers WHERE id = 'new'"))
            migration.downgrade()
        assert [
            column["name"] for column in sa.inspect(connection).get_columns("dossiers")
        ] == ["id", "status"]
    engine.dispose()
