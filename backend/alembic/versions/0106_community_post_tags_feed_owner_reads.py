"""Add global community tags and post associations.

Revision ID: 0106_community_post_tags
Revises: 0105_community_post_media
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0106_community_post_tags"
down_revision: str | None = "0105_community_post_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
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
            "length(trim(name)) > 0",
            name="ck_community_tags_name_not_empty",
        ),
        sa.CheckConstraint(
            "length(trim(slug)) > 0",
            name="ck_community_tags_slug_not_empty",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_community_tags"),
        sa.UniqueConstraint("slug", name="uq_community_tags_slug"),
    )
    op.create_table(
        "community_post_tags",
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            name="fk_community_post_tags_post_id_community_posts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["community_tags.id"],
            name="fk_community_post_tags_tag_id_community_tags",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "post_id",
            "tag_id",
            name="pk_community_post_tags",
        ),
    )
    op.create_index(
        "ix_community_post_tags_tag_post",
        "community_post_tags",
        ["tag_id", "post_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_post_tags_tag_post",
        table_name="community_post_tags",
    )
    op.drop_table("community_post_tags")
    op.drop_table("community_tags")
