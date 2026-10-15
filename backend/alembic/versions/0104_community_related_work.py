"""Link community posts to currently public published work.

Revision ID: 0104_community_related_work
Revises: 0103_community_reports_admin
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0104_community_related_work"
down_revision: str | None = "0103_community_reports_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("community_posts") as batch:
        batch.add_column(sa.Column("related_work_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_community_posts_related_work_id",
            "public_works",
            ["related_work_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index(
            "ix_community_posts_related_work_id",
            ["related_work_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("community_posts") as batch:
        batch.drop_index("ix_community_posts_related_work_id")
        batch.drop_constraint(
            "fk_community_posts_related_work_id",
            type_="foreignkey",
        )
        batch.drop_column("related_work_id")
