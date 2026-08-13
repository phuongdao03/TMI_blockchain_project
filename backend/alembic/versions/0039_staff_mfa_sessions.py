"""Track MFA assurance on application sessions.

Revision ID: 0039_staff_mfa_sessions
Revises: 0038_staff_invitations
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0039_staff_mfa_sessions"
down_revision: str | None = "0038_staff_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("mfa_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "mfa_recovery_authorized_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "mfa_recovery_authorized_at")
    op.drop_column("auth_sessions", "mfa_verified_at")
