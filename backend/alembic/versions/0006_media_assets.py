"""Create Cloudinary media asset metadata.

Revision ID: 0006_media_assets
Revises: 0005_organizations
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_media_assets"
down_revision: str | None = "0005_organizations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MEDIA_STATUS = ("PENDING", "ACTIVE", "QUARANTINED", "DELETED")


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("cloudinary_public_id", sa.Text(), nullable=False),
        sa.Column("cloudinary_version", sa.BigInteger(), nullable=True),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("access_mode", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.CHAR(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                *MEDIA_STATUS,
                name="media_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="PENDING",
        ),
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
        sa.CheckConstraint("bytes >= 0", name="bytes_non_negative"),
        sa.CheckConstraint(
            "cloudinary_version IS NULL OR cloudinary_version >= 0",
            name="cloudinary_version_non_negative",
        ),
        sa.CheckConstraint(
            "width IS NULL OR width >= 0",
            name="width_non_negative",
        ),
        sa.CheckConstraint(
            "height IS NULL OR height >= 0",
            name="height_non_negative",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="duration_ms_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_media_assets_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_assets"),
        sa.UniqueConstraint(
            "cloudinary_public_id",
            name="uq_media_assets_cloudinary_public_id",
        ),
    )
    op.create_index(
        "ix_media_assets_owner_status_created_at",
        "media_assets",
        ["owner_user_id", "status", "created_at"],
    )
    op.create_index(
        "ix_media_assets_status_created_at",
        "media_assets",
        ["status", "created_at"],
    )
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.create_foreign_key(
            "fk_user_profiles_avatar_media_id_media_assets",
            "media_assets",
            ["avatar_media_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_constraint(
            "fk_user_profiles_avatar_media_id_media_assets",
            type_="foreignkey",
        )
    op.drop_table("media_assets")
