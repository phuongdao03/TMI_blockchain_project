"""Create durable public-work favourites.

Revision ID: 0031_public_work_favorites
Revises: 0030_public_work_engagement_daily
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031_public_work_favorites"
down_revision: str | None = "0030_public_work_engagement_daily"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_work_favorites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("public_work_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["public_work_id"],
            ["public_works.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "public_work_id", name="user_work"),
    )
    op.create_index(
        "ix_public_work_favorites_work_created",
        "public_work_favorites",
        ["public_work_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_work_favorites_work_created",
        table_name="public_work_favorites",
    )
    op.drop_table("public_work_favorites")
