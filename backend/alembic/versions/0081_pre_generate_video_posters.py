"""Pre-generate public video posters with the rendition upload.

Revision ID: 0081_pre_generate_video_posters
Revises: 0080_video_renditions
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0081_pre_generate_video_posters"
down_revision: str | None = "0080_video_renditions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rebuild public video renditions so their poster is warm before listing."""
    op.execute(
        sa.text(
            """
            UPDATE public_work_media
            SET derivative_status = 'PENDING',
                failure_code = NULL
            WHERE media_kind = 'VIDEO'
              AND derivative_status = 'READY'
              AND derivative_url LIKE 'https://res.cloudinary.com/%'
              AND public_work_id IN (
                  SELECT id FROM public_works
                  WHERE publication_status = 'PUBLISHED'
              )
            """
        )
    )


def downgrade() -> None:
    pass
