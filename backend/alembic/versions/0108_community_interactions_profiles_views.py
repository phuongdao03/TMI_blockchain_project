"""Add community comment likes, editable profile uniqueness, and post views.

Revision ID: 0108_community_interactions
Revises: 0107_community_write_limits
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0108_community_interactions"
down_revision: str | None = "0107_community_write_limits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("community_posts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "view_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_community_posts_view_count_non_negative",
            "view_count >= 0",
        )

    op.create_index(
        "uq_community_profiles_username_ci",
        "community_profiles",
        [sa.text("lower(username)")],
        unique=True,
    )
    op.create_table(
        "community_comment_likes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comment_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["community_comments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comment_id",
            "user_id",
            name="uq_community_comment_likes_comment_user",
        ),
    )
    op.create_index(
        "ix_community_comment_likes_comment",
        "community_comment_likes",
        ["comment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_comment_likes_comment",
        table_name="community_comment_likes",
    )
    op.drop_table("community_comment_likes")
    op.drop_index(
        "uq_community_profiles_username_ci",
        table_name="community_profiles",
    )
    with op.batch_alter_table("community_posts") as batch_op:
        batch_op.drop_constraint(
            "ck_community_posts_view_count_non_negative",
            type_="check",
        )
        batch_op.drop_column("view_count")
