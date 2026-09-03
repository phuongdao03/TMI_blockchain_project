"""Start reviewer assignments without a conflict gate.

Revision ID: 0070_start_reviews_immediately
Revises: 0069_billing_checkout_link
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0070_start_reviews_immediately"
down_revision: str | None = "0069_billing_checkout_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE review_assignments "
            "SET status = 'IN_PROGRESS' "
            "WHERE status = 'ASSIGNED'"
        )
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TABLE review_assignments "
                "ALTER COLUMN status SET DEFAULT 'IN_PROGRESS'"
            )
        )


def downgrade() -> None:
    # Existing in-progress assignments cannot be separated safely from migrated
    # rows, so rollback preserves their current workflow state.
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TABLE review_assignments "
                "ALTER COLUMN status SET DEFAULT 'ASSIGNED'"
            )
        )
