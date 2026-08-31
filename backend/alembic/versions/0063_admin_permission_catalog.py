"""Seed the fine-grained administration permission catalog.

Revision ID: 0063_admin_permission_catalog
Revises: 0062_user_permissions
Create Date: 2026-08-29
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0063_admin_permission_catalog"
down_revision: str | None = "0062_user_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN_PERMISSION_CODES = (
    "dashboard.read",
    "users.read",
    "users.update",
    "users.suspend",
    "users.sessions.revoke",
    "staff.read",
    "staff.invite",
    "staff.update",
    "staff.permissions.assign",
    "submissions.read",
    "submissions.review",
    "submissions.approve",
    "submissions.reject",
    "payments.read",
    "payments.reconcile",
    "payments.refund",
    "payments.export",
    "blockchain.read",
    "blockchain.retry",
    "storage.read",
    "storage.delete",
    "security.read",
    "security.manage",
    "system.read",
    "system.manage",
    "reports.read",
    "reports.export",
    "settings.read",
    "settings.manage",
)


def _permissions() -> sa.TableClause:
    return sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )


def upgrade() -> None:
    permissions = _permissions()
    bind = op.get_bind()
    existing = set(
        bind.execute(
            sa.select(permissions.c.code).where(
                permissions.c.code.in_(ADMIN_PERMISSION_CODES)
            )
        ).scalars()
    )
    missing = [
        {"id": uuid4(), "code": code}
        for code in ADMIN_PERMISSION_CODES
        if code not in existing
    ]
    if missing:
        bind.execute(permissions.insert(), missing)


def downgrade() -> None:
    permissions = _permissions()
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code.in_(ADMIN_PERMISSION_CODES))
    )
