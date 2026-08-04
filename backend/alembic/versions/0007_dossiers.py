"""Create dossier categories, versions and status history.

Revision ID: 0007_dossiers
Revises: 0006_media_assets
Create Date: 2026-07-30
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_dossiers"
down_revision: str | None = "0006_media_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOSSIER_STATUS = (
    "DRAFT",
    "SUBMITTED",
    "PRECHECK",
    "NEEDS_SUPPLEMENT",
    "UNDER_REVIEW",
    "COUNCIL_REVIEW",
    "APPROVED",
    "REJECTED",
    "PAYMENT_PENDING",
    "PAID",
    "ANCHOR_PENDING",
    "ANCHORED",
    "CERTIFICATE_ISSUED",
    "PUBLISHED",
    "REVOKED",
    "CANCELLED",
)
VISIBILITY = ("PRIVATE", "UNLISTED", "PUBLIC")
CATEGORY_ID = UUID("4d28db19-1507-5a45-a50d-cd0aa83029ec")


def _enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
    )


def _timestamps() -> tuple[sa.Column[sa.DateTime], ...]:
    return (
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
    )


def upgrade() -> None:
    categories = op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name="display_order_non_negative",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("code", name="uq_categories_code"),
    )
    op.bulk_insert(
        categories,
        [
            {
                "id": CATEGORY_ID,
                "code": "DIGITAL_INTELLECTUAL_ASSET",
                "name": "Tài sản trí tuệ số",
                "description": ("Hồ sơ đề nghị xác lập chứng thư tài sản trí tuệ số."),
                "is_active": True,
                "display_order": 0,
            }
        ],
    )

    op.create_table(
        "dossiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=280), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            _enum(DOSSIER_STATUS, "dossier_status"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "visibility",
            _enum(VISIBILITY, "visibility"),
            nullable=False,
            server_default="PRIVATE",
        ),
        sa.Column(
            "current_version_no",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "current_version_no >= 0",
            name="current_version_no_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_dossiers_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_dossiers_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_dossiers_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dossiers"),
        sa.UniqueConstraint("code", name="uq_dossiers_code"),
        sa.UniqueConstraint("slug", name="uq_dossiers_slug"),
    )
    op.create_index(
        "ix_dossiers_owner_status_created_at",
        "dossiers",
        ["owner_user_id", "status", "created_at"],
    )
    op.create_index(
        "ix_dossiers_organization_status",
        "dossiers",
        ["organization_id", "status"],
    )

    snapshot_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
    op.create_table(
        "dossier_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", snapshot_type, nullable=False),
        sa.Column("canonical_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("submitted_by", sa.Uuid(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("version_no > 0", name="version_no_positive"),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_dossier_versions_dossier_id_dossiers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["users.id"],
            name="fk_dossier_versions_submitted_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dossier_versions"),
        sa.UniqueConstraint(
            "dossier_id",
            "version_no",
            name="uq_dossier_versions_dossier_id_version_no",
        ),
    )

    op.create_table(
        "dossier_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column(
            "from_status",
            _enum(DOSSIER_STATUS, "dossier_status_history_from"),
            nullable=False,
        ),
        sa.Column(
            "to_status",
            _enum(DOSSIER_STATUS, "dossier_status_history_to"),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_dossier_status_history_dossier_id_dossiers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_dossier_status_history_actor_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dossier_status_history"),
    )
    op.create_index(
        "ix_dossier_status_history_dossier_created_at",
        "dossier_status_history",
        ["dossier_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("dossier_status_history")
    op.drop_table("dossier_versions")
    op.drop_table("dossiers")
    op.drop_table("categories")
