"""Add cancelled payment status.

Revision ID: 0040_payment_cancelled_status
Revises: 0039_staff_mfa_sessions
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0040_payment_cancelled_status"
down_revision: str | None = "0039_staff_mfa_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUSES = (
    "PENDING",
    "PROCESSING",
    "PAID",
    "FAILED",
    "EXPIRED",
    "REFUNDED",
)
NEW_STATUSES = (*OLD_STATUSES, "CANCELLED")


def _payment_status(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(
        *values,
        name="payment_status",
        native_enum=False,
        create_constraint=True,
    )


def upgrade() -> None:
    with op.batch_alter_table("payment_orders") as batch:
        batch.alter_column(
            "status",
            existing_type=_payment_status(OLD_STATUSES),
            type_=_payment_status(NEW_STATUSES),
            existing_nullable=False,
            existing_server_default="PENDING",
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE payment_orders SET status = 'FAILED' "
            "WHERE status = 'CANCELLED'"
        )
    )
    with op.batch_alter_table("payment_orders") as batch:
        batch.alter_column(
            "status",
            existing_type=_payment_status(NEW_STATUSES),
            type_=_payment_status(OLD_STATUSES),
            existing_nullable=False,
            existing_server_default="PENDING",
        )
