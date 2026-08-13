"""Create daily public-work engagement aggregates.

Revision ID: 0030_engagement_daily
Revises: 0029_ranking_publication
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030_engagement_daily"
down_revision: str | None = "0029_ranking_publication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_work_engagement_daily",
        sa.Column("public_work_id", sa.Uuid(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column(
            "unique_views",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "share_events",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "qr_scans",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "report_requests",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("unique_views >= 0", name="unique_views_non_negative"),
        sa.CheckConstraint("share_events >= 0", name="share_events_non_negative"),
        sa.CheckConstraint("qr_scans >= 0", name="qr_scans_non_negative"),
        sa.CheckConstraint(
            "report_requests >= 0",
            name="report_requests_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["public_work_id"],
            ["public_works.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("public_work_id", "metric_date"),
    )
    op.create_index(
        "ix_public_work_engagement_daily_date_work",
        "public_work_engagement_daily",
        ["metric_date", "public_work_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_work_engagement_daily_date_work",
        table_name="public_work_engagement_daily",
    )
    op.drop_table("public_work_engagement_daily")
