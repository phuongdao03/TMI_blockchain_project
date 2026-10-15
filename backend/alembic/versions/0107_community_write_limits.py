"""Expand community report reasons to match the product form.

Revision ID: 0107_community_write_limits
Revises: 0106_community_post_tags
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0107_community_write_limits"
down_revision: str | None = "0106_community_post_tags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_REPORT_REASONS = (
    "'SPAM', 'HARASSMENT', 'HATE_SPEECH', 'MISINFORMATION', 'COPYRIGHT', "
    "'ADVERTISING', 'PRIVACY_VIOLATION', 'OTHER'"
)
LEGACY_REPORT_REASONS = (
    "'SPAM', 'HARASSMENT', 'HATE_SPEECH', 'MISINFORMATION', "
    "'COPYRIGHT', 'OTHER'"
)


def upgrade() -> None:
    with op.batch_alter_table("community_reports") as batch_op:
        batch_op.drop_constraint("ck_community_reports_reason_valid", type_="check")
        batch_op.create_check_constraint(
            "ck_community_reports_reason_valid",
            f"reason IN ({NEW_REPORT_REASONS})",
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE community_reports SET reason = 'OTHER' "
            "WHERE reason IN ('ADVERTISING', 'PRIVACY_VIOLATION')"
        )
    )
    with op.batch_alter_table("community_reports") as batch_op:
        batch_op.drop_constraint("ck_community_reports_reason_valid", type_="check")
        batch_op.create_check_constraint(
            "ck_community_reports_reason_valid",
            f"reason IN ({LEGACY_REPORT_REASONS})",
        )
