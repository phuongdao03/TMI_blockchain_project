"""Versioned promotion policies, history-safe claims and popup states."""

from uuid import uuid4
import sqlalchemy as sa

from alembic import op

revision = "0146_promotion_management"
down_revision = "0145_login_vouchers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = [
        sa.Column("public_code", sa.String(64)),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("internal_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "program_type", sa.String(16), nullable=False, server_default="CLAIM"
        ),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("policy_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "budget_reserved_vnd", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "budget_spent_vnd", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id")),
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
    ]
    with op.batch_alter_table("voucher_campaigns") as batch:
        for column in columns:
            batch.add_column(column)
        batch.create_index("ix_voucher_campaigns_status", ["status"])
        batch.create_unique_constraint("uq_voucher_campaigns_public_code", ["public_code"])
        batch.create_check_constraint(
            "budget_nonnegative", "budget_reserved_vnd >= 0 AND budget_spent_vnd >= 0"
        )
    with op.batch_alter_table("voucher_claims") as batch:
        batch.add_column(
            sa.Column("issuance_slot", sa.Integer(), nullable=False, server_default="1")
        )
        batch.drop_constraint("uq_voucher_claims_user_campaign", type_="unique")
        batch.create_unique_constraint(
            "uq_voucher_claims_user_campaign_slot",
            ["user_id", "campaign_id", "issuance_slot"],
        )
        for column in [
            sa.Column("policy_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column(
                "policy_version", sa.Integer(), nullable=False, server_default="1"
            ),
            sa.Column(
                "status", sa.String(16), nullable=False, server_default="AVAILABLE"
            ),
            sa.Column("unique_code", sa.String(64)),
            sa.Column("valid_from", sa.DateTime(timezone=True)),
            sa.Column("redeemed_at", sa.DateTime(timezone=True)),
            sa.Column("uses_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "issue_reason", sa.String(255), nullable=False, server_default="claim"
            ),
        ]:
            batch.add_column(column)
        batch.create_unique_constraint("uq_voucher_claims_unique_code", ["unique_code"])
        batch.create_index("ix_voucher_claims_status", ["status"])
    op.create_table(
        "voucher_presentation_states",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("seen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("clicked_at", sa.DateTime(timezone=True)),
        sa.Column("dismissed_at", sa.DateTime(timezone=True)),
        sa.Column("opt_out", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_session_id", sa.Uuid()),
    )
    permissions = sa.table("permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
    for code in ("promotions.manage", "promotions.read"):
        if not op.get_bind().scalar(sa.select(permissions.c.id).where(permissions.c.code == code)):
            op.bulk_insert(permissions, [{"id": uuid4(), "code": code}])
    op.execute(sa.text("UPDATE voucher_campaigns SET name = title"))
    op.execute(
        sa.text(
            "UPDATE voucher_campaigns SET status='DRAFT', active=false, program_type='AUTO' WHERE code='EARLY_MEMBER_2026'"
        )
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM voucher_claims")):
        raise RuntimeError("Preserve promotion snapshots before downgrade.")
    op.drop_table("voucher_presentation_states")
    with op.batch_alter_table("voucher_claims") as batch:
        batch.drop_constraint("uq_voucher_claims_user_campaign_slot", type_="unique")
        batch.drop_column("issuance_slot")
        batch.create_unique_constraint(
            "uq_voucher_claims_user_campaign", ["user_id", "campaign_id"]
        )
        batch.drop_constraint("uq_voucher_claims_unique_code", type_="unique")
        batch.drop_index("ix_voucher_claims_status")
        for name in (
            "policy_json",
            "policy_version",
            "status",
            "unique_code",
            "valid_from",
            "redeemed_at",
            "uses_used",
            "issue_reason",
        ):
            batch.drop_column(name)
    with op.batch_alter_table("voucher_campaigns") as batch:
        batch.drop_constraint("uq_voucher_campaigns_public_code", type_="unique")
        batch.drop_index("ix_voucher_campaigns_status")
        batch.drop_constraint("budget_nonnegative", type_="check")
        for name in (
            "public_code",
            "name",
            "internal_description",
            "status",
            "program_type",
            "policy_version",
            "policy_json",
            "budget_reserved_vnd",
            "budget_spent_vnd",
            "created_by",
            "created_at",
            "updated_at",
        ):
            batch.drop_column(name)
