"""Durable promotion audience jobs and normalized media assets."""

import sqlalchemy as sa

from alembic import op

revision = "0148_promotion_distribution_media"
down_revision = "0147_promotion_checkout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promotion_expiry_reminders",
        sa.Column(
            "voucher_id",
            sa.Uuid(),
            sa.ForeignKey("voucher_claims.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "notified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "promotion_media_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("alt_text", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "promotion_audience_previews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("selector_hash", sa.String(64), nullable=False),
        sa.Column("candidates_json", sa.JSON(), nullable=False),
        sa.Column("eligible_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_promotion_audience_previews_campaign_id",
        "promotion_audience_previews",
        ["campaign_id"],
    )
    op.create_table(
        "promotion_distribution_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "preview_id",
            sa.Uuid(),
            sa.ForeignKey("promotion_audience_previews.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("candidates_json", sa.JSON(), nullable=False),
        sa.Column("cursor", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("issued_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("errors_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "actor_id", "idempotency_key", name="uq_promotion_distribution_actor_key"
        ),
    )
    op.create_index(
        "ix_promotion_distribution_jobs_campaign_id",
        "promotion_distribution_jobs",
        ["campaign_id"],
    )
    op.create_index(
        "ix_promotion_distribution_jobs_status",
        "promotion_distribution_jobs",
        ["status"],
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text("SELECT count(*) FROM promotion_distribution_jobs")
    ) or op.get_bind().scalar(sa.text("SELECT count(*) FROM promotion_media_assets")):
        raise RuntimeError(
            "Preserve promotion distribution and media history before downgrade."
        )
    op.drop_table("promotion_distribution_jobs")
    op.drop_table("promotion_expiry_reminders")
    op.drop_table("promotion_audience_previews")
    op.drop_table("promotion_media_assets")
