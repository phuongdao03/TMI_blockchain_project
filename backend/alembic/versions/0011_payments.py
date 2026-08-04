"""Create payment orders and provider events.

Revision ID: 0011_payments
Revises: 0010_council
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_payments"
down_revision: str | None = "0010_council"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAYMENT_STATUSES = (
    "PENDING",
    "PROCESSING",
    "PAID",
    "FAILED",
    "EXPIRED",
    "REFUNDED",
)


def upgrade() -> None:
    op.create_table(
        "payment_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_code", sa.String(length=32), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_order_id", sa.String(length=128), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *PAYMENT_STATUSES,
                name="payment_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "amount_minor > 0",
            name="amount_minor_positive",
        ),
        sa.CheckConstraint("length(currency) = 3", name="currency_length"),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_payment_orders_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_orders"),
        sa.UniqueConstraint("order_code", name="uq_payment_orders_order_code"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_payment_orders_idempotency_key",
        ),
    )
    op.create_index(
        "ix_payment_orders_dossier_status",
        "payment_orders",
        ["dossier_id", "status"],
    )
    op.create_index(
        "ix_payment_orders_provider_provider_order_id",
        "payment_orders",
        ["provider", "provider_order_id"],
        unique=True,
    )
    op.create_table(
        "payment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_order_id", sa.Uuid(), nullable=False),
        sa.Column("provider_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column("payload_redacted", sa.JSON(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["payment_order_id"],
            ["payment_orders.id"],
            name="fk_payment_events_payment_order_id_payment_orders",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_events"),
        sa.UniqueConstraint(
            "provider_event_id",
            name="uq_payment_events_provider_event_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_index(
        "ix_payment_orders_provider_provider_order_id",
        table_name="payment_orders",
    )
    op.drop_index(
        "ix_payment_orders_dossier_status",
        table_name="payment_orders",
    )
    op.drop_table("payment_orders")
