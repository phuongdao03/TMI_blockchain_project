"""Add structured evidence links and findings to reviewer assessments.

Revision ID: 0056_review_assessment_findings
Revises: 0055_seed_default_dossier_types
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0056_review_assessment_findings"
down_revision: str | None = "0055_seed_default_dossier_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("reviews") as batch:
        batch.add_column(
            sa.Column(
                "criterion_evidence",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.add_column(
            sa.Column(
                "findings",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("reviews") as batch:
        batch.drop_column("findings")
        batch.drop_column("criterion_evidence")
