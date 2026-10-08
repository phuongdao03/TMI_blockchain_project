"""Store a small public poster for retained legacy videos.

Revision ID: 0100_video_poster_cache
Revises: 0099_work_allocation_completion
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0100_video_poster_cache"
down_revision: str | None = "0099_work_allocation_completion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("public_work_media", sa.Column("poster_jpeg", sa.LargeBinary()))
    op.add_column(
        "public_work_media",
        sa.Column("poster_ready", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("public_work_media", "poster_ready")
    op.drop_column("public_work_media", "poster_jpeg")
