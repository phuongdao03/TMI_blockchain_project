"""Add overtime request foundation.

Revision ID: 0085_overtime_foundation
Revises: 0084_leave_foundation
Create Date: 2026-09-20
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0085_overtime_foundation"
down_revision: str | None = "0084_leave_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OVERTIME_PERMISSION_CODES = (
    "hr.overtime.read",
    "hr.overtime.manage",
)


def upgrade() -> None:
    op.create_table(
        "overtime_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
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
            name="overtime_request_status",
        ),
        sa.CheckConstraint("end_at > start_at", name="overtime_request_time_range"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_overtime_requests_employee_status_created",
        "overtime_requests",
        ["employee_id", "status", "created_at"],
    )
    op.create_index(
        "ix_overtime_requests_status_start_at",
        "overtime_requests",
        ["status", "start_at"],
    )

    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    bind = op.get_bind()
    existing = set(
        bind.execute(
            sa.select(permissions.c.code).where(
                permissions.c.code.in_(OVERTIME_PERMISSION_CODES)
            )
        ).scalars()
    )
    missing = [
        {"id": uuid4(), "code": code}
        for code in OVERTIME_PERMISSION_CODES
        if code not in existing
    ]
    if missing:
        bind.execute(permissions.insert(), missing)


def downgrade() -> None:
    permissions = sa.table("permissions", sa.column("code", sa.String()))
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code.in_(OVERTIME_PERMISSION_CODES))
    )
    op.drop_index(
        "ix_overtime_requests_status_start_at", table_name="overtime_requests"
    )
    op.drop_index(
        "ix_overtime_requests_employee_status_created",
        table_name="overtime_requests",
    )
    op.drop_table("overtime_requests")
