"""Add opt-in recent search history.

Revision ID: 0020_search_history
Revises: 0019_oauth_identities
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_search_history"
down_revision: str | None = "0019_oauth_identities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_history_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
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
            ["user_id"],
            ["users.id"],
            name="fk_search_history_preferences_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_search_history_preferences"),
    )
    op.create_table(
        "search_history_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_query", sa.String(length=200), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("searched_at", sa.DateTime(timezone=True), nullable=False),
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
            ["user_id"],
            ["users.id"],
            name="fk_search_history_entries_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_search_history_entries"),
    )
    op.create_index(
        "uq_search_history_entries_user_query_hash",
        "search_history_entries",
        ["user_id", "query_hash"],
        unique=True,
    )
    op.create_index(
        "ix_search_history_entries_user_searched",
        "search_history_entries",
        ["user_id", "searched_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_history_entries_user_searched",
        table_name="search_history_entries",
    )
    op.drop_index(
        "uq_search_history_entries_user_query_hash",
        table_name="search_history_entries",
    )
    op.drop_table("search_history_entries")
    op.drop_table("search_history_preferences")
