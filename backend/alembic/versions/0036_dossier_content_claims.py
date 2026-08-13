"""Add immutable exact-content claims for dossier submission deduplication.

Revision ID: 0036_dossier_content_claims
Revises: 0035_engagement_velocity
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036_dossier_content_claims"
down_revision: str | None = "0035_engagement_velocity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dossier_content_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_fingerprint", sa.CHAR(length=64), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_dossier_content_claims_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"],
            ["dossier_versions.id"],
            name="fk_dossier_content_claims_dossier_version_id_dossier_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dossier_content_claims"),
        sa.UniqueConstraint(
            "content_fingerprint",
            name="uq_dossier_content_claims_fingerprint",
        ),
    )
    op.create_index(
        "ix_dossier_content_claims_dossier_id",
        "dossier_content_claims",
        ["dossier_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dossier_content_claims_dossier_id",
        table_name="dossier_content_claims",
    )
    op.drop_table("dossier_content_claims")
