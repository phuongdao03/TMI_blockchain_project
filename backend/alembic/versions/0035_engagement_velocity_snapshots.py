"""Create isolated engagement discovery velocity snapshots.

Revision ID: 0035_engagement_velocity_snapshots
Revises: 0034_engagement_analytics_snapshots
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0035_engagement_velocity_snapshots"
down_revision: str | None = "0034_engagement_analytics_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "engagement_velocity_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("formula_version", sa.String(length=64), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "window_end >= window_start",
            name="velocity_window_valid",
        ),
        sa.CheckConstraint(
            "candidate_count >= 0",
            name="velocity_candidate_count_non_negative",
        ),
        sa.CheckConstraint(
            "total_score >= 0",
            name="velocity_total_score_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "window_start",
            "window_end",
            name="uq_engagement_velocity_snapshots_window",
        ),
    )
    op.create_index(
        "ix_engagement_velocity_snapshots_window_end",
        "engagement_velocity_snapshots",
        ["window_end"],
    )
    op.create_table(
        "engagement_velocity_snapshot_items",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("public_work_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Numeric(20, 8), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("rank > 0", name="velocity_rank_positive"),
        sa.CheckConstraint(
            "display_order > 0",
            name="velocity_display_order_positive",
        ),
        sa.CheckConstraint("score >= 0", name="velocity_score_non_negative"),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["engagement_velocity_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["public_work_id"],
            ["public_works.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("snapshot_id", "public_work_id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "display_order",
            name="uq_engagement_velocity_snapshot_items_display_order",
        ),
    )
    op.create_index(
        "ix_engagement_velocity_snapshot_items_snapshot_rank",
        "engagement_velocity_snapshot_items",
        ["snapshot_id", "rank", "display_order"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_engagement_velocity_snapshot_items_snapshot_rank",
        table_name="engagement_velocity_snapshot_items",
    )
    op.drop_table("engagement_velocity_snapshot_items")
    op.drop_index(
        "ix_engagement_velocity_snapshots_window_end",
        table_name="engagement_velocity_snapshots",
    )
    op.drop_table("engagement_velocity_snapshots")
