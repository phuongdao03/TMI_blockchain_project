from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy import String

from app.db.alembic_compat import ensure_alembic_version_capacity


class FakeConnection:
    def __init__(self, dialect: str = "postgresql") -> None:
        self.dialect = SimpleNamespace(name=dialect)
        self.statements: list[str] = []

    def exec_driver_sql(self, statement: str) -> None:
        self.statements.append(statement)


def test_existing_postgres_version_table_is_widened() -> None:
    connection = FakeConnection()
    inspector = Mock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{"name": "version_num", "type": String(32)}]

    with patch("app.db.alembic_compat.inspect", return_value=inspector):
        ensure_alembic_version_capacity(connection)

    assert connection.statements == [
        "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"
    ]


def test_new_postgres_version_table_uses_wide_revision_column() -> None:
    connection = FakeConnection()
    inspector = Mock()
    inspector.has_table.return_value = False

    with patch("app.db.alembic_compat.inspect", return_value=inspector):
        ensure_alembic_version_capacity(connection)

    assert connection.statements == [
        "CREATE TABLE IF NOT EXISTS alembic_version ("
        "version_num VARCHAR(128) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    ]


def test_already_wide_postgres_version_table_is_unchanged() -> None:
    connection = FakeConnection()
    inspector = Mock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{"name": "version_num", "type": String(128)}]

    with patch("app.db.alembic_compat.inspect", return_value=inspector):
        ensure_alembic_version_capacity(connection)

    assert connection.statements == []


def test_non_postgres_version_table_is_left_to_alembic() -> None:
    connection = FakeConnection("sqlite")

    ensure_alembic_version_capacity(connection)

    assert connection.statements == []
