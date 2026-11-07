"""Add topic-specific follows for Community posts.

Revision ID: 0158_community_post_follows
Revises: 0157_wallet_topup_terms
"""

import sqlalchemy as sa

from alembic import op

revision = "0158_community_post_follows"
down_revision = "0157_wallet_topup_terms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "community_post_follows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            name="fk_community_post_follows_post_id_community_posts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_community_post_follows_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "post_id",
            "user_id",
            name="uq_community_post_follows_post_user",
        ),
    )
    op.create_index(
        "ix_community_post_follows_user_created",
        "community_post_follows",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_community_post_follows_post",
        "community_post_follows",
        ["post_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_post_follows_post",
        table_name="community_post_follows",
    )
    op.drop_index(
        "ix_community_post_follows_user_created",
        table_name="community_post_follows",
    )
    op.drop_table("community_post_follows")
