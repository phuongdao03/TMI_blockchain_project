"""Track recent human activity for idle session expiry.

Revision ID: 0142_auth_session_idle_timeout
Revises: 0141_membership_chat_history
"""

import sqlalchemy as sa

from alembic import op

revision = "0142_auth_session_idle_timeout"
down_revision = "0141_membership_chat_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE auth_sessions "
            "SET last_activity_at = created_at "
            "WHERE last_activity_at IS NULL"
        )
    )
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.alter_column(
            "last_activity_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )


def downgrade() -> None:
    op.drop_column("auth_sessions", "last_activity_at")
