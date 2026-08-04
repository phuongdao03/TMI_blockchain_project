"""Create opaque public QR share links.

Revision ID: 0032_public_share_links
Revises: 0031_public_work_favorites
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032_public_share_links"
down_revision: str | None = "0031_public_work_favorites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_share_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_work_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["public_work_id"],
            ["public_works.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_public_share_links_work_created",
        "public_share_links",
        ["public_work_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_share_links_work_created",
        table_name="public_share_links",
    )
    op.drop_table("public_share_links")
