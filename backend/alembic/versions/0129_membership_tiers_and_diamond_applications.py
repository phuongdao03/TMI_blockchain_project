"""Add Silver catalog, immutable purchase price snapshots, and Diamond review.

Revision ID: 0129_membership_tiers_and_diamond_applications
Revises: 0128_community_membership
"""

from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision = "0129_membership_tiers_and_diamond_applications"
down_revision = "0128_community_membership"
branch_labels = None
depends_on = None

SILVER_PLAN_ID = UUID("46d85051-6fb7-4fa9-93f4-09d9cfa9d041")
GOLD_PLAN_ID = UUID("3cdb1ac9-c51b-4c37-b4da-2bf43a03b7a7")
DIAMOND_PLAN_ID = UUID("f5e84512-8e10-4e2b-9c5e-dc5e7f16f774")


def _table_count(table_name: str) -> int:
    return int(
        op.get_bind()
        .execute(sa.text(f"SELECT COUNT(*) FROM {table_name}"))
        .scalar_one()
    )


def upgrade() -> None:
    with op.batch_alter_table("membership_plans") as batch:
        batch.drop_constraint("valid_tier", type_="check")
        batch.create_check_constraint(
            "valid_tier", "tier IN ('SILVER', 'COMPANION', 'PRESTIGE')"
        )

    op.add_column(
        "membership_purchases",
        sa.Column("list_price_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "membership_purchases",
        sa.Column("credit_minor", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.execute(
        sa.text(
            "UPDATE membership_purchases "
            "SET list_price_minor = amount_minor WHERE list_price_minor IS NULL"
        )
    )
    with op.batch_alter_table("membership_purchases") as batch:
        batch.alter_column(
            "list_price_minor", existing_type=sa.BigInteger(), nullable=False
        )
        batch.create_check_constraint(
            "valid_price_snapshot",
            "list_price_minor >= amount_minor AND credit_minor >= 0",
        )
    op.create_index(
        "ix_membership_purchases_owner_tier_expiry",
        "membership_purchases",
        ["user_id", "tier", "expires_at"],
    )

    op.create_table(
        "membership_diamond_applications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("decision_note", sa.Text()),
        sa.Column(
            "reviewed_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
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
            "status IN ('PENDING', 'INFO_REQUESTED', 'APPROVED', 'REJECTED')",
            name="valid_status",
        ),
        sa.CheckConstraint(
            "length(trim(statement)) BETWEEN 1 AND 5000", name="statement_length"
        ),
        sa.CheckConstraint(
            "decision_note IS NULL OR length(trim(decision_note)) <= 2000",
            name="decision_note_length",
        ),
    )
    op.create_index(
        "ix_membership_diamond_applications_user_id",
        "membership_diamond_applications",
        ["user_id"],
    )
    op.create_index(
        "uq_membership_diamond_applications_open_user",
        "membership_diamond_applications",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('PENDING', 'INFO_REQUESTED')"),
        postgresql_where=sa.text("status IN ('PENDING', 'INFO_REQUESTED')"),
    )

    plans = sa.table(
        "membership_plans",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String(120)),
        sa.column("tier", sa.String(16)),
        sa.column("amount_minor", sa.BigInteger()),
        sa.column("duration_days", sa.Integer()),
        sa.column("active", sa.Boolean()),
    )
    bind = op.get_bind()
    for identifier, name, tier, amount in (
        (SILVER_PLAN_ID, "Kết nối", "SILVER", 490_000),
        (GOLD_PLAN_ID, "Đồng hành", "COMPANION", 1_490_000),
        (DIAMOND_PLAN_ID, "Tinh hoa", "PRESTIGE", 3_990_000),
    ):
        existing = bind.scalar(
            sa.select(plans.c.id)
            .where(plans.c.tier == tier, plans.c.active.is_(True))
            .limit(1)
        )
        if existing is None:
            bind.execute(
                plans.insert().values(
                    id=identifier,
                    name=name,
                    tier=tier,
                    amount_minor=amount,
                    duration_days=365,
                    active=True,
                )
            )


def downgrade() -> None:
    if (
        _table_count("membership_purchases")
        or _table_count("user_memberships")
        or _table_count("membership_diamond_applications")
    ):
        raise RuntimeError(
            "Archive membership history before downgrading membership tiers."
        )

    op.drop_index(
        "uq_membership_diamond_applications_open_user",
        table_name="membership_diamond_applications",
    )
    op.drop_index(
        "ix_membership_diamond_applications_user_id",
        table_name="membership_diamond_applications",
    )
    op.drop_table("membership_diamond_applications")
    op.drop_index(
        "ix_membership_purchases_owner_tier_expiry",
        table_name="membership_purchases",
    )
    with op.batch_alter_table("membership_purchases") as batch:
        batch.drop_constraint("valid_price_snapshot", type_="check")
        batch.drop_column("credit_minor")
        batch.drop_column("list_price_minor")

    op.execute(
        sa.delete(sa.table("membership_plans", sa.column("id", sa.Uuid()))).where(
            sa.column("id", sa.Uuid()).in_(
                [SILVER_PLAN_ID, GOLD_PLAN_ID, DIAMOND_PLAN_ID]
            )
        )
    )
    with op.batch_alter_table("membership_plans") as batch:
        batch.drop_constraint("valid_tier", type_="check")
        batch.create_check_constraint("valid_tier", "tier IN ('COMPANION', 'PRESTIGE')")
