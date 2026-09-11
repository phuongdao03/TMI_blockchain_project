"""Add portable public video presentation settings.

Revision ID: 0075_public_video_presentation
Revises: 0074_expand_video_evidence_limit
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0075_public_video_presentation"
down_revision: str | None = "0074_expand_video_evidence_limit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.add_column(
            sa.Column(
                "storage_provider",
                sa.String(length=32),
                nullable=False,
                server_default="CLOUDINARY",
            )
        )
        batch_op.add_column(
            sa.Column("provider_asset_id", sa.String(length=255), nullable=True)
        )
        batch_op.create_unique_constraint(
            "uq_media_assets_provider_asset",
            ["storage_provider", "provider_asset_id"],
        )
    with op.batch_alter_table("public_work_media") as batch_op:
        batch_op.add_column(
            sa.Column("poster_media_asset_id", sa.Uuid(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "video_controls_preset",
                sa.String(length=16),
                nullable=False,
                server_default="FULL",
            )
        )
        batch_op.add_column(
            sa.Column(
                "video_fit_mode",
                sa.String(length=16),
                nullable=False,
                server_default="CONTAIN",
            )
        )
        batch_op.add_column(
            sa.Column(
                "video_quality_profile",
                sa.String(length=16),
                nullable=False,
                server_default="BALANCED",
            )
        )
        batch_op.add_column(
            sa.Column(
                "video_max_width",
                sa.Integer(),
                nullable=False,
                server_default="1280",
            )
        )
        batch_op.add_column(
            sa.Column(
                "video_autoplay",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "video_loop", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.add_column(
            sa.Column(
                "video_muted", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.create_foreign_key(
            "fk_public_work_media_poster_media_asset_id",
            "media_assets",
            ["poster_media_asset_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint(
            "ck_public_work_media_video_controls_preset",
            "video_controls_preset IN ('FULL', 'MINIMAL', 'NONE')",
        )
        batch_op.create_check_constraint(
            "ck_public_work_media_video_fit_mode",
            "video_fit_mode IN ('CONTAIN', 'COVER')",
        )
        batch_op.create_check_constraint(
            "ck_public_work_media_video_quality_profile",
            "video_quality_profile IN ('DATA_SAVER', 'BALANCED', 'HIGH')",
        )
        batch_op.create_check_constraint(
            "ck_public_work_media_video_max_width_supported",
            "video_max_width IN (640, 960, 1280, 1920)",
        )


def downgrade() -> None:
    with op.batch_alter_table("public_work_media") as batch_op:
        batch_op.drop_constraint(
            "ck_public_work_media_video_max_width_supported", type_="check"
        )
        batch_op.drop_constraint(
            "ck_public_work_media_video_quality_profile", type_="check"
        )
        batch_op.drop_constraint("ck_public_work_media_video_fit_mode", type_="check")
        batch_op.drop_constraint(
            "ck_public_work_media_video_controls_preset", type_="check"
        )
        batch_op.drop_constraint(
            "fk_public_work_media_poster_media_asset_id", type_="foreignkey"
        )
        for column in (
            "video_muted",
            "video_loop",
            "video_autoplay",
            "video_max_width",
            "video_quality_profile",
            "video_fit_mode",
            "video_controls_preset",
            "poster_media_asset_id",
        ):
            batch_op.drop_column(column)
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.drop_constraint("uq_media_assets_provider_asset", type_="unique")
        batch_op.drop_column("provider_asset_id")
        batch_op.drop_column("storage_provider")
