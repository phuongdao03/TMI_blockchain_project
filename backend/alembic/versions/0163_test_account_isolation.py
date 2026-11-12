"""Add server-owned TEST markers without changing existing account history."""

import sqlalchemy as sa

from alembic import op

revision = "0163_test_account_isolation"
down_revision = "0162_pending_submission_snapshots"
branch_labels = None
depends_on = None


TEST_MARKER_COLUMNS = (
    ("users", "is_test_account"),
    ("staff_invitations", "is_test_account"),
    ("dossiers", "is_test"),
    ("fee_obligations", "is_test"),
    ("payment_orders", "is_test"),
)


def upgrade() -> None:
    for table, column in TEST_MARKER_COLUMNS:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(
                    column,
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        if table == "users" and op.get_bind().dialect.name == "sqlite":
            op.execute("DROP INDEX IF EXISTS ux_users_email_nocase")
            op.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_nocase "
                "ON users(email COLLATE NOCASE)"
            )


def downgrade() -> None:
    bind = op.get_bind()
    marked_rows = sum(
        int(
            bind.scalar(sa.text(f"SELECT count(*) FROM {table} WHERE {column} = 1"))
            or 0
        )
        for table, column in TEST_MARKER_COLUMNS
    )
    if marked_rows:
        raise RuntimeError("Cannot downgrade while TEST account data exists.")
    for table, column in reversed(TEST_MARKER_COLUMNS):
        with op.batch_alter_table(table) as batch:
            batch.drop_column(column)
        if table == "users" and bind.dialect.name == "sqlite":
            op.execute("DROP INDEX IF EXISTS ux_users_email_nocase")
            op.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_nocase "
                "ON users(email COLLATE NOCASE)"
            )
