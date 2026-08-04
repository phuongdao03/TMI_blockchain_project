"""Create immutable hourly trending score snapshots.

Revision ID: 0028_trending_snapshots
Revises: 0027_category_ranking
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028_trending_snapshots"
down_revision: str | None = "0027_category_ranking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trending_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("formula_version", sa.String(64), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("result_digest", sa.String(64), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "window_end > window_start",
            name="ck_trending_snapshots_window_valid",
        ),
        sa.CheckConstraint(
            "length(source_digest) = 64",
            name="ck_trending_snapshots_source_digest_length",
        ),
        sa.CheckConstraint(
            "length(result_digest) = 64",
            name="ck_trending_snapshots_result_digest_length",
        ),
        sa.CheckConstraint(
            "candidate_count >= 0",
            name="ck_trending_snapshots_candidate_count_non_negative",
        ),
        sa.CheckConstraint(
            "total_score >= 0",
            name="ck_trending_snapshots_total_score_non_negative",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trending_snapshots"),
        sa.UniqueConstraint(
            "window_start",
            "window_end",
            name="uq_trending_snapshots_window",
        ),
    )
    op.create_index(
        "ix_trending_snapshots_window_end",
        "trending_snapshots",
        ["window_end"],
    )
    op.create_table(
        "trending_snapshot_items",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("score", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("rank > 0", name="ck_trending_snapshot_items_rank_positive"),
        sa.CheckConstraint(
            "display_order > 0",
            name="ck_trending_snapshot_items_display_order_positive",
        ),
        sa.CheckConstraint(
            "score >= 0",
            name="ck_trending_snapshot_items_score_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["trending_snapshots.id"],
            name="fk_trending_snapshot_items_snapshot_id_trending_snapshots",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["public_works.id"],
            name="fk_trending_snapshot_items_work_id_public_works",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_trending_snapshot_items_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            "work_id",
            name="pk_trending_snapshot_items",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "display_order",
            name="uq_trending_snapshot_items_display_order",
        ),
    )
    op.create_index(
        "ix_trending_snapshot_items_snapshot_rank",
        "trending_snapshot_items",
        ["snapshot_id", "rank", "display_order"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trending_snapshot_items_snapshot_rank",
        table_name="trending_snapshot_items",
    )
    op.drop_table("trending_snapshot_items")
    op.drop_index("ix_trending_snapshots_window_end", table_name="trending_snapshots")
    op.drop_table("trending_snapshots")
