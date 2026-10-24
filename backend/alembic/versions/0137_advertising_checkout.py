"""Add advertising wallet orders and membership discount policies.

Revision ID: 0137_advertising_checkout
Revises: 0136_advertising_inventory
"""

from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0137_advertising_checkout"
down_revision = "0136_advertising_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "advertising_discount_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("rate_basis_points", sa.Integer(), nullable=False),
        sa.Column("annual_allowance_vnd", sa.BigInteger(), nullable=False),
        sa.Column("policy_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rate_basis_points BETWEEN 0 AND 10000",
            name="ck_advertising_discount_policies_valid_rate",
        ),
        sa.CheckConstraint(
            "annual_allowance_vnd >= 0",
            name="ck_advertising_discount_policies_allowance_nonnegative",
        ),
        sa.CheckConstraint(
            "policy_version > 0",
            name="ck_advertising_discount_policies_version_positive",
        ),
        sa.CheckConstraint(
            "tier IN ('MEMBER', 'SILVER', 'COMPANION', 'PRESTIGE')",
            name="ck_advertising_discount_policies_valid_tier",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tier", name="uq_advertising_discount_policies_tier"),
    )
    op.create_table(
        "advertising_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("price_version", sa.Integer(), nullable=False),
        sa.Column("membership_tier", sa.String(length=16), nullable=False),
        sa.Column("membership_cycle_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discount_policy_version", sa.Integer(), nullable=False),
        sa.Column("base_amount_vnd", sa.BigInteger(), nullable=False),
        sa.Column("discount_amount_vnd", sa.BigInteger(), nullable=False),
        sa.Column("payable_amount_vnd", sa.BigInteger(), nullable=False),
        sa.Column(
            "payment_status",
            sa.String(length=24),
            server_default="PENDING_PAYMENT",
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payment_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("wallet_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("allowance_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "pricing_snapshot",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "base_amount_vnd >= 0",
            name="ck_advertising_orders_base_nonnegative",
        ),
        sa.CheckConstraint(
            "discount_amount_vnd >= 0",
            name="ck_advertising_orders_discount_nonnegative",
        ),
        sa.CheckConstraint(
            "payable_amount_vnd = base_amount_vnd - discount_amount_vnd",
            name="ck_advertising_orders_amounts_balanced",
        ),
        sa.CheckConstraint(
            "payable_amount_vnd >= 0",
            name="ck_advertising_orders_payable_nonnegative",
        ),
        sa.CheckConstraint(
            "payment_status IN ('PENDING_PAYMENT', 'PAID', 'EXPIRED', "
            "'REFUND_PENDING', 'REFUNDED')",
            name="ck_advertising_orders_valid_payment_status",
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["advertising_reservations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["advertising_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["package_id"], ["advertising_packages.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["wallet_transaction_id"], ["wallet_journals.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id", name="uq_ad_orders_reservation"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_ad_orders_user_key"),
        sa.UniqueConstraint("wallet_transaction_id"),
    )
    op.create_index(
        "ix_advertising_orders_user_created",
        "advertising_orders",
        ["user_id", "created_at"],
    )

    policy_table = sa.table(
        "advertising_discount_policies",
        sa.column("id", sa.Uuid()),
        sa.column("tier", sa.String()),
        sa.column("rate_basis_points", sa.Integer()),
        sa.column("annual_allowance_vnd", sa.BigInteger()),
        sa.column("policy_version", sa.Integer()),
        sa.column("active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        policy_table,
        [
            {
                "id": UUID(identifier),
                "tier": tier,
                "rate_basis_points": rate,
                "annual_allowance_vnd": allowance,
                "policy_version": 1,
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
            for identifier, tier, rate, allowance in [
                ("a1370000-0000-4000-8000-000000000001", "MEMBER", 0, 0),
                ("a1370000-0000-4000-8000-000000000002", "SILVER", 500, 150_000),
                ("a1370000-0000-4000-8000-000000000003", "COMPANION", 1000, 600_000),
                ("a1370000-0000-4000-8000-000000000004", "PRESTIGE", 1500, 2_000_000),
            ]
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_advertising_orders_user_created", table_name="advertising_orders")
    op.drop_table("advertising_orders")
    op.drop_table("advertising_discount_policies")
