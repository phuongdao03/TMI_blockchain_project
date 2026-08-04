"""Add public work media derivatives.

Revision ID: 0016_public_media
Revises: 0015_public_taxonomy
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_public_media"
down_revision: str | None = "0015_public_taxonomy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_work_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_work_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "media_kind",
            sa.Enum(
                "IMAGE",
                "AUDIO",
                "VIDEO",
                "DOCUMENT",
                name="public_media_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("caption", sa.String(length=500), nullable=True),
        sa.Column("alt_text", sa.String(length=500), nullable=True),
        sa.Column(
            "derivative_status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "READY",
                "FAILED",
                name="public_media_derivative_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("derivative_url", sa.Text(), nullable=True),
        sa.Column("derivative_public_id", sa.Text(), nullable=True),
        sa.Column("derivative_mime_type", sa.String(length=127), nullable=True),
        sa.Column("derivative_width", sa.Integer(), nullable=True),
        sa.Column("derivative_height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
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
        sa.CheckConstraint(
            "sort_order >= 0", name="ck_public_work_media_sort_order_non_negative"
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_public_work_media_attempt_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["public_work_id"],
            ["public_works.id"],
            name="fk_public_work_media_public_work_id_public_works",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name="fk_public_work_media_media_asset_id_media_assets",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_public_work_media"),
        sa.UniqueConstraint(
            "public_work_id",
            "media_asset_id",
            name="uq_public_work_media_work_asset",
        ),
    )
    op.create_index(
        "ix_public_work_media_work_order",
        "public_work_media",
        ["public_work_id", "sort_order", "created_at"],
    )
    op.create_index(
        "ix_public_work_media_derivative_status",
        "public_work_media",
        ["derivative_status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_work_media_derivative_status", table_name="public_work_media"
    )
    op.drop_index("ix_public_work_media_work_order", table_name="public_work_media")
    op.drop_table("public_work_media")
