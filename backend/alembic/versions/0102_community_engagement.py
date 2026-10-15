"""Add community profiles and engagement relations.

Revision ID: 0102_community_engagement
Revises: 0101_community_foundation
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0102_community_engagement"
down_revision: str | None = "0101_community_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("bio", sa.String(length=500), nullable=True),
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
            "length(trim(username)) > 0",
            name="ck_community_profiles_username_not_empty",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("username", name="uq_community_profiles_username"),
    )
    op.create_index(
        "ix_community_profiles_display_name",
        "community_profiles",
        ["display_name"],
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO community_profiles (user_id, username) "
            "SELECT id, 'member-' || replace(CAST(id AS VARCHAR), '-', '') "
            "FROM users"
        )
    )

    op.create_table(
        "community_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_community_comments_content_not_empty",
        ),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_community_comments_parent_not_self",
        ),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["community_comments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["community_posts.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_community_comments_post_parent_created",
        "community_comments",
        ["post_id", "parent_id", "created_at", "id"],
    )

    op.create_table(
        "community_likes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
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
            ["post_id"], ["community_posts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_community_likes_post_user"),
    )
    op.create_index("ix_community_likes_post", "community_likes", ["post_id"])

    op.create_table(
        "community_bookmarks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
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
            ["post_id"], ["community_posts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "post_id", "user_id", name="uq_community_bookmarks_post_user"
        ),
    )
    op.create_index(
        "ix_community_bookmarks_user_created",
        "community_bookmarks",
        ["user_id", "created_at"],
    )

    op.create_table(
        "community_follows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("follower_user_id", sa.Uuid(), nullable=False),
        sa.Column("followed_user_id", sa.Uuid(), nullable=False),
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
            "follower_user_id <> followed_user_id",
            name="ck_community_follows_self_follow_not_allowed",
        ),
        sa.ForeignKeyConstraint(["followed_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["follower_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "follower_user_id", "followed_user_id", name="uq_community_follows_pair"
        ),
    )
    op.create_index(
        "ix_community_follows_followed",
        "community_follows",
        ["followed_user_id"],
    )
    op.create_index(
        "ix_community_follows_follower",
        "community_follows",
        ["follower_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_community_follows_follower", table_name="community_follows")
    op.drop_index("ix_community_follows_followed", table_name="community_follows")
    op.drop_table("community_follows")
    op.drop_index(
        "ix_community_bookmarks_user_created", table_name="community_bookmarks"
    )
    op.drop_table("community_bookmarks")
    op.drop_index("ix_community_likes_post", table_name="community_likes")
    op.drop_table("community_likes")
    op.drop_index(
        "ix_community_comments_post_parent_created",
        table_name="community_comments",
    )
    op.drop_table("community_comments")
    op.drop_index("ix_community_profiles_display_name", table_name="community_profiles")
    op.drop_table("community_profiles")
