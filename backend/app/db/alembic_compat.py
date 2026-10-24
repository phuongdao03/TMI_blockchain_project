from sqlalchemy import Connection, inspect

ALEMBIC_VERSION_COLUMN_LENGTH = 128


def ensure_alembic_version_capacity(connection: Connection) -> None:
    if connection.dialect.name != "postgresql":
        return

    inspector = inspect(connection)
    if not inspector.has_table("alembic_version"):
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            f"version_num VARCHAR({ALEMBIC_VERSION_COLUMN_LENGTH}) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        return

    version_column = next(
        (
            column
            for column in inspector.get_columns("alembic_version")
            if column["name"] == "version_num"
        ),
        None,
    )
    if version_column is None:
        raise RuntimeError("alembic_version is missing its version_num column")

    current_length = getattr(version_column["type"], "length", None)
    if current_length is None or current_length >= ALEMBIC_VERSION_COLUMN_LENGTH:
        return

    connection.exec_driver_sql(
        "ALTER TABLE alembic_version ALTER COLUMN version_num "
        f"TYPE VARCHAR({ALEMBIC_VERSION_COLUMN_LENGTH})"
    )
