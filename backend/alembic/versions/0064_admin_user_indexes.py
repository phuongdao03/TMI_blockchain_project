"""Add indexes for administration user queries.

Revision ID: 0064_admin_user_indexes
Revises: 0063_admin_permission_catalog
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0064_admin_user_indexes"
down_revision: str | None = "0063_admin_permission_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index(
        "ix_users_status_created_at",
        "users",
        ["status", "created_at"],
    )
    op.create_index("ix_users_last_login_at", "users", ["last_login_at"])
    op.create_index(
        "ix_auth_identities_provider_user_id",
        "auth_identities",
        ["provider", "user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_identities_provider_user_id",
        table_name="auth_identities",
    )
    op.drop_index("ix_users_last_login_at", table_name="users")
    op.drop_index("ix_users_status_created_at", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
