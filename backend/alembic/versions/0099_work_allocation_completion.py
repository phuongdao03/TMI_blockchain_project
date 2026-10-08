"""Track completion by each general-work assignee.

Revision ID: 0099_work_allocation_completion
Revises: 0098_certificate_content_drafts
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0099_work_allocation_completion"
down_revision: str | None = "0098_certificate_content_drafts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "allocation_members",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("allocation_members", "completed_at")
