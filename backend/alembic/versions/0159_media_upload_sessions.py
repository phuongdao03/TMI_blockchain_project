"""Add idempotent upload session identifiers to media assets."""

import sqlalchemy as sa

from alembic import op

revision = "0159_media_upload_sessions"
down_revision = "0158_community_post_follows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column("upload_session_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "uq_media_assets_upload_session_id",
        "media_assets",
        ["upload_session_id"],
        unique=True,
        postgresql_where=sa.text("upload_session_id IS NOT NULL"),
        sqlite_where=sa.text("upload_session_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_media_assets_upload_session_id",
        table_name="media_assets",
    )
    op.drop_column("media_assets", "upload_session_id")
