"""Add versioned billing price catalog.

Revision ID: 0067_billing_price_catalog
Revises: 0066_type_specific_review_rubric
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0067_billing_price_catalog"
down_revision: str | None = "0066_type_specific_review_rubric"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "price_catalog_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="DRAFT"
        ),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("version_no > 0", name="version_no_positive"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'RETIRED')",
            name="status_values",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="effective_interval_valid",
        ),
        sa.CheckConstraint(
            "status != 'PUBLISHED' OR published_at IS NOT NULL",
            name="published_has_timestamp",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_no"),
    )
    op.create_index(
        "ix_price_catalog_versions_status_effective",
        "price_catalog_versions",
        ["status", "effective_from", "effective_to"],
    )
    op.create_table(
        "price_catalog_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("catalog_version_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_type_id", sa.Uuid(), nullable=False),
        sa.Column("service_code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "tax_mode",
            sa.String(length=32),
            nullable=False,
            server_default="UNSPECIFIED",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        sa.CheckConstraint("length(currency) = 3", name="currency_length"),
        sa.ForeignKeyConstraint(
            ["catalog_version_id"],
            ["price_catalog_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_type_id"], ["dossier_types.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "catalog_version_id",
            "dossier_type_id",
            "service_code",
            name="uq_price_catalog_entry_scope",
        ),
    )
    op.create_index(
        "ix_price_catalog_entries_dossier_type_id",
        "price_catalog_entries",
        ["dossier_type_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_price_catalog_entries_dossier_type_id",
        table_name="price_catalog_entries",
    )
    op.drop_table("price_catalog_entries")
    op.drop_index(
        "ix_price_catalog_versions_status_effective",
        table_name="price_catalog_versions",
    )
    op.drop_table("price_catalog_versions")
