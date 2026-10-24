"""Tiered membership, purchase snapshots and community chat.

Revision ID: 0128_community_membership
Revises: 0127_internal_wallet
"""

from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision = "0128_community_membership"
down_revision = "0127_internal_wallet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
        ),
        [
            {
                "id": UUID("8b8a370a-81a6-4329-8d68-a5cf86d5b725"),
                "code": "memberships.manage",
            }
        ],
    )
    op.create_table(
        "membership_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("tier IN ('COMPANION', 'PRESTIGE')", name="valid_tier"),
        sa.CheckConstraint(
            "amount_minor > 0 AND amount_minor <= 1000000000", name="amount_range"
        ),
        sa.CheckConstraint("duration_days BETWEEN 1 AND 3660", name="duration_range"),
    )
    op.create_table(
        "user_memberships",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "plan_id",
            sa.Uuid(),
            sa.ForeignKey("membership_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "membership_purchases",
        sa.Column(
            "id",
            sa.Uuid(),
            sa.ForeignKey("wallet_journals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.Uuid(),
            sa.ForeignKey("membership_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount_minor > 0", name="positive_amount"),
    )
    op.create_index(
        "ix_membership_purchases_user_id", "membership_purchases", ["user_id"]
    )
    op.create_table(
        "community_chat_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("room", sa.String(16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("tier_snapshot", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "room IN ('MEMBER', 'COMPANION', 'PRESTIGE')", name="valid_room"
        ),
        sa.CheckConstraint("length(trim(body)) BETWEEN 1 AND 2000", name="body_length"),
    )
    op.create_index(
        "ix_community_chat_messages_user_id", "community_chat_messages", ["user_id"]
    )
    op.create_index(
        "ix_community_chat_messages_room", "community_chat_messages", ["room"]
    )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(sa.text("SELECT COUNT(*) FROM membership_purchases"))
        .scalar()
    ):
        raise RuntimeError(
            "Archive purchased memberships before rolling back their schema."
        )
    op.drop_table("community_chat_messages")
    op.drop_table("membership_purchases")
    op.drop_table("user_memberships")
    op.drop_table("membership_plans")
    op.execute(sa.text("DELETE FROM permissions WHERE code = 'memberships.manage'"))
