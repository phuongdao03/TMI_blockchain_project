"""Track upload purpose and ordered community post image attachments.

Revision ID: 0105_community_post_media
Revises: 0104_community_related_work
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0105_community_post_media"
down_revision: str | None = "0104_community_related_work"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.add_column(sa.Column("purpose", sa.String(length=32), nullable=True))
        batch.create_check_constraint(
            "purpose_valid",
            "purpose IS NULL OR purpose IN "
            "('AVATAR', 'DOSSIER_EVIDENCE', 'PUBLIC_WORK', 'PUBLIC_COVER', "
            "'COMMUNITY_POST')",
        )
        batch.create_index(
            "ix_media_assets_purpose_owner_status",
            ["purpose", "owner_user_id", "status"],
        )

    op.create_table(
        "community_post_media",
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name="fk_community_post_media_media_asset_id_media_assets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            name="fk_community_post_media_post_id_community_posts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "post_id",
            "media_asset_id",
            name="pk_community_post_media",
        ),
        sa.UniqueConstraint(
            "media_asset_id",
            name="uq_community_post_media_asset",
        ),
        sa.UniqueConstraint(
            "post_id",
            "sort_order",
            name="uq_community_post_media_order",
        ),
    )
    op.create_index(
        "ix_community_post_media_post_order",
        "community_post_media",
        ["post_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_post_media_post_order",
        table_name="community_post_media",
    )
    op.drop_table("community_post_media")
    with op.batch_alter_table("media_assets") as batch:
        batch.drop_index("ix_media_assets_purpose_owner_status")
        batch.drop_constraint("purpose_valid", type_="check")
        batch.drop_column("purpose")
