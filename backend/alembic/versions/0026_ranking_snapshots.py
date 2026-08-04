"""Create immutable versioned ranking snapshots.

Revision ID: 0026_ranking_snapshots
Revises: 0025_voting_vote_permissions
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026_ranking_snapshots"
down_revision: str | None = "0025_voting_vote_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ranking_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("formula_version", sa.String(64), nullable=False),
        sa.Column("campaign_rule_version", sa.Integer(), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("result_digest", sa.String(64), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("total_valid_votes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version > 0",
            name="ck_ranking_snapshots_version_positive",
        ),
        sa.CheckConstraint(
            "campaign_rule_version > 0",
            name="ck_ranking_snapshots_rule_version_positive",
        ),
        sa.CheckConstraint(
            "length(source_digest) = 64",
            name="ck_ranking_snapshots_source_digest_length",
        ),
        sa.CheckConstraint(
            "length(result_digest) = 64",
            name="ck_ranking_snapshots_result_digest_length",
        ),
        sa.CheckConstraint(
            "candidate_count >= 0",
            name="ck_ranking_snapshots_candidate_count_non_negative",
        ),
        sa.CheckConstraint(
            "total_valid_votes >= 0",
            name="ck_ranking_snapshots_total_votes_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["voting_campaigns.id"],
            name="fk_ranking_snapshots_campaign_id_voting_campaigns",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ranking_snapshots"),
        sa.UniqueConstraint(
            "campaign_id",
            "version",
            name="uq_ranking_snapshots_campaign_version",
        ),
    )
    op.create_index(
        "ix_ranking_snapshots_campaign_created",
        "ranking_snapshots",
        ["campaign_id", "created_at"],
    )
    op.create_table(
        "ranking_snapshot_items",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("score", sa.BigInteger(), nullable=False),
        sa.Column("effective_vote_count", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "rank > 0",
            name="ck_ranking_snapshot_items_rank_positive",
        ),
        sa.CheckConstraint(
            "display_order > 0",
            name="ck_ranking_snapshot_items_display_order_positive",
        ),
        sa.CheckConstraint(
            "score >= 0",
            name="ck_ranking_snapshot_items_score_non_negative",
        ),
        sa.CheckConstraint(
            "effective_vote_count >= 0",
            name="ck_ranking_snapshot_items_vote_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["ranking_snapshots.id"],
            name="fk_ranking_snapshot_items_snapshot_id_ranking_snapshots",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["public_works.id"],
            name="fk_ranking_snapshot_items_work_id_public_works",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            "work_id",
            name="pk_ranking_snapshot_items",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "display_order",
            name="uq_ranking_snapshot_items_snapshot_display_order",
        ),
    )
    op.create_index(
        "ix_ranking_snapshot_items_snapshot_rank",
        "ranking_snapshot_items",
        ["snapshot_id", "rank", "display_order"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ranking_snapshot_items_snapshot_rank",
        table_name="ranking_snapshot_items",
    )
    op.drop_table("ranking_snapshot_items")
    op.drop_index(
        "ix_ranking_snapshots_campaign_created",
        table_name="ranking_snapshots",
    )
    op.drop_table("ranking_snapshots")
