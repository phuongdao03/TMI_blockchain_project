"""Add leave request foundation.

Revision ID: 0084_leave_foundation
Revises: 0083_attendance_foundation
Create Date: 2026-09-20
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0084_leave_foundation"
down_revision: str | None = "0083_attendance_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEAVE_PERMISSION_CODES = (
    "hr.leave.read",
    "hr.leave.manage",
)


def upgrade() -> None:
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("leave_type", sa.String(64), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("decision_note", sa.Text()),
        sa.Column("reviewed_by_user_id", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="leave_request_status",
        ),
        sa.CheckConstraint("end_date >= start_date", name="leave_request_date_range"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_leave_requests_employee_status_created",
        "leave_requests",
        ["employee_id", "status", "created_at"],
    )
    op.create_index(
        "ix_leave_requests_status_start_date",
        "leave_requests",
        ["status", "start_date"],
    )

    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    bind = op.get_bind()
    existing = set(
        bind.execute(
            sa.select(permissions.c.code).where(
                permissions.c.code.in_(LEAVE_PERMISSION_CODES)
            )
        ).scalars()
    )
    missing = [
        {"id": uuid4(), "code": code}
        for code in LEAVE_PERMISSION_CODES
        if code not in existing
    ]
    if missing:
        bind.execute(permissions.insert(), missing)


def downgrade() -> None:
    permissions = sa.table("permissions", sa.column("code", sa.String()))
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code.in_(LEAVE_PERMISSION_CODES))
    )
    op.drop_index("ix_leave_requests_status_start_date", table_name="leave_requests")
    op.drop_index(
        "ix_leave_requests_employee_status_created", table_name="leave_requests"
    )
    op.drop_table("leave_requests")
