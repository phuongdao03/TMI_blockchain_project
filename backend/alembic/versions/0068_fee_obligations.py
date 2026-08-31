"""Add durable fee obligations.

Revision ID: 0068_fee_obligations
Revises: 0067_billing_price_catalog
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0068_fee_obligations"
down_revision: str | None = "0067_billing_price_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fee_obligations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("price_catalog_version_id", sa.Uuid(), nullable=False),
        sa.Column("price_catalog_entry_id", sa.Uuid(), nullable=False),
        sa.Column("service_code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("tax_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price_snapshot_json", sa.JSON(), nullable=False),
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
        sa.CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        sa.CheckConstraint("length(currency) = 3", name="currency_length"),
        sa.CheckConstraint(
            "status IN ('OPEN', 'OVERDUE', 'PAID', 'WAIVED', 'CANCELLED')",
            name="status_values",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"], ["dossiers.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["price_catalog_version_id"],
            ["price_catalog_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["price_catalog_entry_id"],
            ["price_catalog_entries.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dossier_id", name="uq_fee_obligations_dossier_id"),
    )
    op.create_index(
        "ix_fee_obligations_owner_status_due",
        "fee_obligations",
        ["owner_user_id", "status", "due_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fee_obligations_owner_status_due", table_name="fee_obligations"
    )
    op.drop_table("fee_obligations")
