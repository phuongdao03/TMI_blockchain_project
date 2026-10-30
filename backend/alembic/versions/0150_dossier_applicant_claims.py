"""Add private applicant claims and optimistic concurrency to existing dossiers."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0150_dossier_applicant_claims"
down_revision = "0149_review_evidence_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dossiers",
        sa.Column(
            "claims_json",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "dossiers",
        sa.Column("claims_revision", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    table = sa.table("dossiers", sa.column("claims_revision", sa.Integer()))
    if op.get_bind().scalar(
        sa.select(sa.func.count()).select_from(table).where(table.c.claims_revision > 0)
    ):
        raise RuntimeError(
            "Applicant claims have been edited; retain them and roll forward."
        )
    op.drop_column("dossiers", "claims_revision")
    op.drop_column("dossiers", "claims_json")
