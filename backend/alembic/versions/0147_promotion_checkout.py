"""Atomic voucher reservations and append-only financial adjustments."""

import sqlalchemy as sa
from alembic import op

revision = "0147_promotion_checkout"
down_revision = "0146_promotion_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voucher_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "voucher_id",
            sa.Uuid(),
            sa.ForeignKey("voucher_claims.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("order_reference", sa.String(180), nullable=False),
        sa.Column("service_code", sa.String(40), nullable=False),
        sa.Column("product_id", sa.String(64)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("original_vnd", sa.BigInteger(), nullable=False),
        sa.Column("discount_vnd", sa.BigInteger(), nullable=False),
        sa.Column("payable_vnd", sa.BigInteger(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "discount_vnd > 0 AND original_vnd >= discount_vnd AND payable_vnd = original_vnd - discount_vnd",
            name="balanced_amounts",
        ),
        sa.CheckConstraint(
            "status IN ('HELD','REDEEMED','RELEASED')", name="valid_status"
        ),
    )
    for name, cols in [
        ("ix_voucher_reservations_voucher_id", ["voucher_id"]),
        ("ix_voucher_reservations_user_id", ["user_id"]),
        ("ix_voucher_reservations_campaign_status", ["campaign_id", "status"]),
    ]:
        op.create_index(name, "voucher_reservations", cols)
    op.create_index(
        "uq_voucher_active_order",
        "voucher_reservations",
        ["order_reference"],
        unique=True,
        postgresql_where=sa.text("status IN ('HELD','REDEEMED')"),
        sqlite_where=sa.text("status IN ('HELD','REDEEMED')"),
    )
    op.create_table(
        "voucher_adjustments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "reservation_id",
            sa.Uuid(),
            sa.ForeignKey("voucher_reservations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(180), nullable=False, unique=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("discount_vnd", sa.BigInteger(), nullable=False),
        sa.Column("refund_vnd", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "discount_vnd >= 0 AND refund_vnd >= 0", name="amounts_nonnegative"
        ),
    )
    op.create_index(
        "ix_voucher_adjustments_reservation_id",
        "voucher_adjustments",
        ["reservation_id"],
    )
    with op.batch_alter_table("payment_orders") as batch:
        batch.drop_constraint(
            op.f("ck_payment_orders_amount_minor_positive"), type_="check"
        )
        batch.create_check_constraint("amount_minor_positive", "amount_minor >= 0")
    with op.batch_alter_table("membership_purchases") as batch:
        batch.add_column(
            sa.Column(
                "wallet_journal_id",
                sa.Uuid(),
                sa.ForeignKey(
                    "wallet_journals.id",
                    name="fk_membership_purchases_wallet_journal_id_wallet_journals",
                    ondelete="RESTRICT",
                ),
            )
        )
        batch.drop_constraint(
            op.f("fk_membership_purchases_id_wallet_journals"), type_="foreignkey"
        )
        batch.drop_constraint(
            op.f("ck_membership_purchases_positive_amount"), type_="check"
        )
        batch.create_check_constraint("positive_amount", "amount_minor >= 0")
    op.execute(sa.text("UPDATE membership_purchases SET wallet_journal_id = id"))


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM voucher_reservations")):
        raise RuntimeError(
            "Voucher reservation/usage history must be preserved before downgrade."
        )
    if op.get_bind().scalar(
        sa.text("SELECT count(*) FROM payment_orders WHERE amount_minor = 0")
    ) or op.get_bind().scalar(
        sa.text("SELECT count(*) FROM membership_purchases WHERE amount_minor = 0")
    ):
        raise RuntimeError(
            "Zero-payable promotion orders must be preserved before downgrade."
        )
    with op.batch_alter_table("payment_orders") as batch:
        batch.drop_constraint(
            op.f("ck_payment_orders_amount_minor_positive"), type_="check"
        )
        batch.create_check_constraint("amount_minor_positive", "amount_minor > 0")
    with op.batch_alter_table("membership_purchases") as batch:
        batch.drop_constraint(
            "fk_membership_purchases_wallet_journal_id_wallet_journals",
            type_="foreignkey",
        )
        batch.drop_column("wallet_journal_id")
        batch.create_foreign_key(
            "fk_membership_purchases_id_wallet_journals",
            "wallet_journals",
            ["id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.drop_constraint(
            op.f("ck_membership_purchases_positive_amount"), type_="check"
        )
        batch.create_check_constraint("positive_amount", "amount_minor > 0")
    op.drop_table("voucher_adjustments")
    op.drop_table("voucher_reservations")
