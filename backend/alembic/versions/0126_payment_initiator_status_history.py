"""Track payment initiators and status transitions.

Revision ID: 0126_payment_initiator_status_history
Revises: 0125_neutral_payment_guides
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0126_payment_initiator_status_history"
down_revision: str | None = "0125_neutral_payment_guides"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("payment_orders") as batch:
        batch.add_column(sa.Column("initiated_by_user_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_payment_orders_initiated_by_user_id_users",
            "users",
            ["initiated_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index(
            "ix_payment_orders_initiated_by_user_id",
            ["initiated_by_user_id"],
        )

    op.create_table(
        "payment_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_order_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["payment_order_id"], ["payment_orders.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_status_history_order_changed",
        "payment_status_history",
        ["payment_order_id", "changed_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_status_history_order_changed",
        table_name="payment_status_history",
    )
    op.drop_table("payment_status_history")
    with op.batch_alter_table("payment_orders") as batch:
        batch.drop_index("ix_payment_orders_initiated_by_user_id")
        batch.drop_constraint(
            "fk_payment_orders_initiated_by_user_id_users",
            type_="foreignkey",
        )
        batch.drop_column("initiated_by_user_id")
