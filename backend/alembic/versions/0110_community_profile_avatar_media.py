"""Attach inspected media assets to community profile avatars.

Revision ID: 0110_community_avatar_media
Revises: 0109_community_admin_workspaces
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0110_community_avatar_media"
down_revision: str | None = "0109_community_admin_workspaces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("community_profiles") as batch_op:
        batch_op.add_column(sa.Column("avatar_media_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_community_profiles_avatar_media_id_media_assets",
            "media_assets",
            ["avatar_media_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "uq_community_profiles_avatar_media_id",
            ["avatar_media_id"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("community_profiles") as batch_op:
        batch_op.drop_index("uq_community_profiles_avatar_media_id")
        batch_op.drop_constraint(
            "fk_community_profiles_avatar_media_id_media_assets",
            type_="foreignkey",
        )
        batch_op.drop_column("avatar_media_id")
