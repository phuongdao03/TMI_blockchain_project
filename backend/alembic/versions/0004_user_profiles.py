"""Create encrypted user profile storage.

Revision ID: 0004_user_profiles
Revises: 0003_registration_outbox
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_user_profiles"
down_revision: str | None = "0003_registration_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("avatar_media_id", sa.Uuid(), nullable=True),
        sa.Column(
            "locale",
            sa.String(length=16),
            nullable=False,
            server_default="vi",
        ),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Asia/Ho_Chi_Minh",
        ),
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
            name="fk_user_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_profiles"),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
