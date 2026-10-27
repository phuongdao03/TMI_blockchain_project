import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_preparation_migration_refuses_to_discard_active_input() -> None:
    filename = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/0144_dossier_preparations.py"
    )
    spec = importlib.util.spec_from_file_location("preparation_migration", filename)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE users (id TEXT PRIMARY KEY)"))
        connection.execute(sa.text("CREATE TABLE dossiers (id TEXT PRIMARY KEY)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            connection.execute(
                sa.text(
                    "INSERT INTO dossier_preparations "
                    "(owner_user_id,revision,payload_json) "
                    "VALUES (:owner,1,:payload)"
                ),
                {"owner": "a" * 32, "payload": '{"values":{"title":"Draft input"}}'},
            )
            with pytest.raises(RuntimeError, match="must be preserved"):
                migration.downgrade()
            connection.execute(
                sa.text("UPDATE dossier_preparations SET payload_json=NULL")
            )
            migration.downgrade()
        assert "dossier_preparations" not in sa.inspect(connection).get_table_names()
    engine.dispose()
