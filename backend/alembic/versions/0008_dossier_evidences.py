"""Create mutable draft and immutable version evidence links.

Revision ID: 0008_dossier_evidences
Revises: 0007_dossiers
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_dossier_evidences"
down_revision: str | None = "0007_dossiers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dossier_evidences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=True),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name="display_order_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_dossier_evidences_dossier_id_dossiers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"],
            ["dossier_versions.id"],
            name=("fk_dossier_evidences_dossier_version_id_dossier_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name="fk_dossier_evidences_media_asset_id_media_assets",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dossier_evidences"),
    )
    op.create_index(
        "ix_dossier_evidences_dossier_version_order",
        "dossier_evidences",
        ["dossier_id", "dossier_version_id", "display_order"],
    )


def downgrade() -> None:
    op.drop_table("dossier_evidences")
