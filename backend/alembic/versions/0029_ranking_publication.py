"""Track the selected ranking snapshot published for a campaign.

Revision ID: 0029_ranking_publication
Revises: 0028_trending_snapshots
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029_ranking_publication"
down_revision: str | None = "0028_trending_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "voting_campaigns",
        sa.Column("published_snapshot_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "voting_campaigns",
        sa.Column("results_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE voting_campaigns
        SET published_snapshot_id = (
                SELECT ranking_snapshots.id
                FROM ranking_snapshots
                WHERE ranking_snapshots.campaign_id = voting_campaigns.id
                ORDER BY ranking_snapshots.version DESC
                LIMIT 1
            ),
            results_published_at = (
                SELECT ranking_snapshots.created_at
                FROM ranking_snapshots
                WHERE ranking_snapshots.campaign_id = voting_campaigns.id
                ORDER BY ranking_snapshots.version DESC
                LIMIT 1
            )
        WHERE voting_campaigns.status = 'PUBLISHED'
        """
    )
    with op.batch_alter_table("voting_campaigns") as batch_op:
        batch_op.create_foreign_key(
            "fk_voting_campaigns_published_snapshot_id_ranking_snapshots",
            "ranking_snapshots",
            ["published_snapshot_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_voting_campaigns_published_snapshot_id",
        "voting_campaigns",
        ["published_snapshot_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_voting_campaigns_published_snapshot_id",
        table_name="voting_campaigns",
    )
    with op.batch_alter_table("voting_campaigns") as batch_op:
        batch_op.drop_constraint(
            "fk_voting_campaigns_published_snapshot_id_ranking_snapshots",
            type_="foreignkey",
        )
        batch_op.drop_column("results_published_at")
        batch_op.drop_column("published_snapshot_id")
