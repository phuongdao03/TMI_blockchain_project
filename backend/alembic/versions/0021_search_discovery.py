"""Add privacy-safe search discovery and analytics snapshots.

Revision ID: 0021_search_discovery
Revises: 0020_search_history
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_search_discovery"
down_revision: str | None = "0020_search_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("query_hash", sa.String(64), nullable=False),
        sa.Column("normalized_query", sa.String(200)),
        sa.Column("category_slug", sa.String(180)),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("selected_work_id", sa.Uuid()),
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
        sa.ForeignKeyConstraint(
            ["selected_work_id"], ["public_works.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        "ix_search_events_created_category",
        "search_events",
        ["created_at", "category_slug"],
    )
    op.create_index(
        "ix_search_events_query_created", "search_events", ["query_hash", "created_at"]
    )
    op.create_table(
        "search_trending_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("query_hash", sa.String(64), nullable=False),
        sa.Column("display_query", sa.String(200), nullable=False),
        sa.Column("search_count", sa.Integer(), nullable=False),
        sa.Column(
            "is_suppressed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "period", "period_start", "query_hash", name="uq_search_trending_period"
        ),
    )
    op.create_index(
        "ix_search_trending_public",
        "search_trending_snapshots",
        ["period", "period_start", "is_suppressed", "search_count"],
    )
    op.create_table(
        "search_suppressed_phrases",
        sa.Column("query_hash", sa.String(64), nullable=False),
        sa.Column("suppressed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["suppressed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("query_hash"),
    )
    op.create_table(
        "search_analytics_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category_slug", sa.String(180), nullable=False, server_default=""),
        sa.Column("search_count", sa.Integer(), nullable=False),
        sa.Column("zero_result_count", sa.Integer(), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False),
        sa.Column("latency_p95_ms", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "period_start", "category_slug", name="uq_search_analytics_period_category"
        ),
    )
    op.create_index(
        "ix_search_analytics_period",
        "search_analytics_snapshots",
        ["period_start", "category_slug"],
    )


def downgrade() -> None:
    op.drop_index("ix_search_analytics_period", table_name="search_analytics_snapshots")
    op.drop_table("search_analytics_snapshots")
    op.drop_table("search_suppressed_phrases")
    op.drop_index("ix_search_trending_public", table_name="search_trending_snapshots")
    op.drop_table("search_trending_snapshots")
    op.drop_index("ix_search_events_query_created", table_name="search_events")
    op.drop_index("ix_search_events_created_category", table_name="search_events")
    op.drop_table("search_events")
