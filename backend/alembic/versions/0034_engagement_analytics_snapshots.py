"""Create daily engagement analytics snapshots.

Revision ID: 0034_engagement_analytics
Revises: 0033_public_work_share_events
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034_engagement_analytics"
down_revision: str | None = "0033_public_work_share_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "engagement_analytics_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("unique_views", sa.BigInteger(), nullable=False),
        sa.Column("share_events", sa.BigInteger(), nullable=False),
        sa.Column("qr_scans", sa.BigInteger(), nullable=False),
        sa.Column("report_requests", sa.BigInteger(), nullable=False),
        sa.Column("favorite_events", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "unique_views >= 0",
            name="engagement_snapshot_unique_views_non_negative",
        ),
        sa.CheckConstraint(
            "share_events >= 0",
            name="engagement_snapshot_share_events_non_negative",
        ),
        sa.CheckConstraint(
            "qr_scans >= 0",
            name="engagement_snapshot_qr_scans_non_negative",
        ),
        sa.CheckConstraint(
            "report_requests >= 0",
            name="engagement_snapshot_report_requests_non_negative",
        ),
        sa.CheckConstraint(
            "favorite_events >= 0",
            name="engagement_snapshot_favorite_events_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "metric_date",
            name="uq_engagement_analytics_snapshots_metric_date",
        ),
    )
    op.create_index(
        "ix_engagement_analytics_snapshots_metric_date",
        "engagement_analytics_snapshots",
        ["metric_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_engagement_analytics_snapshots_metric_date",
        table_name="engagement_analytics_snapshots",
    )
    op.drop_table("engagement_analytics_snapshots")
