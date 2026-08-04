"""Freeze category ranks in ranking snapshot items.

Revision ID: 0027_category_ranking
Revises: 0026_ranking_snapshots
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027_category_ranking"
down_revision: str | None = "0026_ranking_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ranking_snapshot_items",
        sa.Column("category_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "ranking_snapshot_items",
        sa.Column("category_rank", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE ranking_snapshot_items
        SET category_id = (
            SELECT public_works.category_id
            FROM public_works
            WHERE public_works.id = ranking_snapshot_items.work_id
        )
        """
    )
    op.execute(
        """
        UPDATE ranking_snapshot_items AS current_item
        SET category_rank = 1 + (
            SELECT COUNT(*)
            FROM ranking_snapshot_items AS higher_item
            WHERE higher_item.snapshot_id = current_item.snapshot_id
              AND higher_item.category_id = current_item.category_id
              AND higher_item.score > current_item.score
        )
        """
    )
    with op.batch_alter_table("ranking_snapshot_items") as batch_op:
        batch_op.alter_column(
            "category_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        batch_op.alter_column(
            "category_rank",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_ranking_snapshot_items_category_rank_positive",
            "category_rank > 0",
        )
        batch_op.create_foreign_key(
            "fk_ranking_snapshot_items_category_id_categories",
            "categories",
            ["category_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index(
        "ix_ranking_snapshot_items_category_rank",
        "ranking_snapshot_items",
        ["snapshot_id", "category_id", "category_rank", "display_order"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ranking_snapshot_items_category_rank",
        table_name="ranking_snapshot_items",
    )
    with op.batch_alter_table("ranking_snapshot_items") as batch_op:
        batch_op.drop_constraint(
            "fk_ranking_snapshot_items_category_id_categories",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "ck_ranking_snapshot_items_category_rank_positive",
            type_="check",
        )
        batch_op.drop_column("category_rank")
        batch_op.drop_column("category_id")
