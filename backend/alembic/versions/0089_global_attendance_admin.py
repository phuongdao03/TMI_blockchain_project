"""Add global attendance administration permissions.

Revision ID: 0089_global_attendance_admin
Revises: 0088_global_attendance
Create Date: 2026-09-21
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0089_global_attendance_admin"
down_revision: str | None = "0088_global_attendance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GLOBAL_ATTENDANCE_ADMIN_PERMISSION_CODES = (
    "hr.attendance.worksites.read",
    "hr.attendance.worksites.manage",
)


def upgrade() -> None:
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    bind = op.get_bind()
    existing = set(
        bind.execute(
            sa.select(permissions.c.code).where(
                permissions.c.code.in_(GLOBAL_ATTENDANCE_ADMIN_PERMISSION_CODES)
            )
        ).scalars()
    )
    missing = [
        {"id": uuid4(), "code": code}
        for code in GLOBAL_ATTENDANCE_ADMIN_PERMISSION_CODES
        if code not in existing
    ]
    if missing:
        bind.execute(permissions.insert(), missing)


def downgrade() -> None:
    permissions = sa.table("permissions", sa.column("code", sa.String()))
    op.get_bind().execute(
        permissions.delete().where(
            permissions.c.code.in_(GLOBAL_ATTENDANCE_ADMIN_PERMISSION_CODES)
        )
    )
