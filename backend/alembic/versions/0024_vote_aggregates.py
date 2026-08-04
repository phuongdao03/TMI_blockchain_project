"""Create trusted vote aggregates.

Revision ID: 0024_vote_aggregates
Revises: 0023_voting_permissions
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024_vote_aggregates"
down_revision: str | None = "0023_voting_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vote_aggregates",
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column(
            "effective_count", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "effective_count >= 0",
            name="ck_vote_aggregates_effective_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["voting_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["work_id"], ["public_works.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("campaign_id", "work_id"),
    )
    op.create_index(
        "ix_vote_aggregates_campaign_count",
        "vote_aggregates",
        ["campaign_id", "effective_count"],
    )


def downgrade() -> None:
    op.drop_index("ix_vote_aggregates_campaign_count", table_name="vote_aggregates")
    op.drop_table("vote_aggregates")
