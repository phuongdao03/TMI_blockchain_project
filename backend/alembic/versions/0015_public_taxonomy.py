"""Add public catalog taxonomy.

Revision ID: 0015_public_taxonomy
Revises: 0014_public_catalog
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015_public_taxonomy"
down_revision: str | None = "0014_public_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("categories") as batch:
        batch.add_column(sa.Column("parent_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("slug", sa.String(length=160), nullable=True))
        batch.create_foreign_key(
            "fk_categories_parent_id_categories",
            "categories",
            ["parent_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint("uq_categories_slug", ["slug"])

    op.create_table(
        "public_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.PrimaryKeyConstraint("id", name="pk_public_tags"),
        sa.UniqueConstraint("slug", name="uq_public_tags_slug"),
    )
    op.create_table(
        "public_work_tags",
        sa.Column("public_work_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["public_work_id"],
            ["public_works.id"],
            name="fk_public_work_tags_public_work_id_public_works",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["public_tags.id"],
            name="fk_public_work_tags_tag_id_public_tags",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "public_work_id",
            "tag_id",
            name="pk_public_work_tags",
        ),
    )


def downgrade() -> None:
    op.drop_table("public_work_tags")
    op.drop_table("public_tags")
    with op.batch_alter_table("categories") as batch:
        batch.drop_constraint("uq_categories_slug", type_="unique")
        batch.drop_constraint(
            "fk_categories_parent_id_categories",
            type_="foreignkey",
        )
        batch.drop_column("slug")
        batch.drop_column("parent_id")
