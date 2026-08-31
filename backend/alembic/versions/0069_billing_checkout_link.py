"""Link payment checkout sessions to fee obligations.

Revision ID: 0069_billing_checkout_link
Revises: 0068_fee_obligations
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0069_billing_checkout_link"
down_revision: str | None = "0068_fee_obligations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("payment_orders") as batch:
        batch.add_column(sa.Column("fee_obligation_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_payment_orders_fee_obligation_id",
            "fee_obligations",
            ["fee_obligation_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("ix_payment_orders_fee_obligation_id", ["fee_obligation_id"])


def downgrade() -> None:
    with op.batch_alter_table("payment_orders") as batch:
        batch.drop_index("ix_payment_orders_fee_obligation_id")
        batch.drop_constraint("fk_payment_orders_fee_obligation_id", type_="foreignkey")
        batch.drop_column("fee_obligation_id")
