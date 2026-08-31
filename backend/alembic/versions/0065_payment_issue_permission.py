"""Seed permission for issuing dossier payment requests.

Revision ID: 0065_payment_issue_permission
Revises: 0064_admin_user_indexes
Create Date: 2026-08-30
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0065_payment_issue_permission"
down_revision: str | None = "0064_admin_user_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    bind = op.get_bind()
    exists = bind.scalar(
        sa.select(sa.func.count())
        .select_from(permissions)
        .where(permissions.c.code == "payments.issue")
    )
    if not exists:
        bind.execute(permissions.insert().values(id=uuid4(), code="payments.issue"))


def downgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("code", sa.String()),
    )
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code == "payments.issue")
    )
