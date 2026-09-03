"""Store reviewer assessment for every frozen evidence file.

Revision ID: 0072_review_evidence_assessments
Revises: 0071_flexible_dossier_evidence
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0072_review_evidence_assessments"
down_revision: str | None = "0071_flexible_dossier_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column(
            "evidence_assessments",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("reviews", "evidence_assessments")
