"""Requeue published videos for compatible streaming renditions.

Revision ID: 0080_video_renditions
Revises: 0079_backfill_category_slugs
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0080_video_renditions"
down_revision: str | None = "0079_backfill_category_slugs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Reprocess only published videos currently served by the slow proxy."""
    op.execute(
        sa.text(
            """
            UPDATE public_work_media
            SET derivative_status = 'PENDING',
                derivative_url = NULL,
                derivative_public_id = NULL,
                derivative_mime_type = NULL,
                derivative_width = NULL,
                derivative_height = NULL,
                duration_ms = NULL,
                failure_code = NULL
            WHERE media_kind = 'VIDEO'
              AND derivative_status = 'READY'
              AND derivative_url LIKE '/api/v1/public/works/%/media/%'
              AND public_work_id IN (
                  SELECT id
                  FROM public_works
                  WHERE publication_status = 'PUBLISHED'
              )
            """
        )
    )


def downgrade() -> None:
    # The previous proxy URL cannot be reconstructed without losing rendition data.
    pass
