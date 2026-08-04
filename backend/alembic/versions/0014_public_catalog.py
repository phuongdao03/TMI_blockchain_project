"""Create public work projection and slug history.

Revision ID: 0014_public_catalog
Revises: 0013_operations
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_public_catalog"
down_revision: str | None = "0013_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    publication_status = sa.Enum(
        "DRAFT",
        "PENDING_PUBLICATION",
        "PUBLISHED",
        "HIDDEN",
        "SUSPENDED",
        "ARCHIVED",
        name="publication_status",
        native_enum=False,
        create_constraint=True,
    )
    visibility = sa.Enum(
        "PRIVATE",
        "UNLISTED",
        "PUBLIC",
        name="public_work_visibility",
        native_enum=False,
        create_constraint=True,
    )
    op.create_table(
        "public_works",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("certificate_id", sa.Uuid(), nullable=True),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("short_description", sa.String(length=500), nullable=False),
        sa.Column("full_description", sa.Text(), nullable=True),
        sa.Column(
            "publication_status",
            publication_status,
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "visibility",
            visibility,
            nullable=False,
            server_default="PRIVATE",
        ),
        sa.Column("author_display_name", sa.String(length=255), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("thumbnail_media_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("featured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("featured_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "view_count >= 0",
            name="view_count_non_negative",
        ),
        sa.CheckConstraint("version > 0", name="version_positive"),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_public_works_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            ["certificates.id"],
            name="fk_public_works_certificate_id_certificates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_public_works_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_public_works_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_public_works_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["thumbnail_media_id"],
            ["media_assets.id"],
            name="fk_public_works_thumbnail_media_id_media_assets",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_public_works"),
        sa.UniqueConstraint("dossier_id", name="uq_public_works_dossier_id"),
        sa.UniqueConstraint("slug", name="uq_public_works_slug"),
    )
    op.create_index(
        "ix_public_works_status_visibility_published",
        "public_works",
        ["publication_status", "visibility", "published_at"],
    )
    op.create_index(
        "ix_public_works_category_status_visibility",
        "public_works",
        ["category_id", "publication_status", "visibility"],
    )
    op.create_table(
        "public_work_slug_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_work_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["public_work_id"],
            ["public_works.id"],
            name="fk_public_work_slug_history_public_work_id_public_works",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_public_work_slug_history"),
        sa.UniqueConstraint("slug", name="uq_public_work_slug_history_slug"),
    )
    op.create_index(
        "ix_public_work_slug_history_work_created",
        "public_work_slug_history",
        ["public_work_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_work_slug_history_work_created",
        table_name="public_work_slug_history",
    )
    op.drop_table("public_work_slug_history")
    op.drop_index(
        "ix_public_works_category_status_visibility",
        table_name="public_works",
    )
    op.drop_index(
        "ix_public_works_status_visibility_published",
        table_name="public_works",
    )
    op.drop_table("public_works")
