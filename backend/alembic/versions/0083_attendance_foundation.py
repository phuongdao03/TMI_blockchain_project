"""Add attendance foundation.

Revision ID: 0083_attendance_foundation
Revises: 0082_hr_foundation
Create Date: 2026-09-20
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0083_attendance_foundation"
down_revision: str | None = "0082_hr_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ATTENDANCE_PERMISSION_CODES = (
    "hr.attendance.read",
    "hr.attendance.adjust",
)


def upgrade() -> None:
    op.create_table(
        "attendance",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("check_in_at", sa.DateTime(timezone=True)),
        sa.Column("check_out_at", sa.DateTime(timezone=True)),
        sa.Column("check_in_latitude", sa.Numeric(9, 6)),
        sa.Column("check_in_longitude", sa.Numeric(9, 6)),
        sa.Column("check_out_latitude", sa.Numeric(9, 6)),
        sa.Column("check_out_longitude", sa.Numeric(9, 6)),
        sa.Column("status", sa.String(16), server_default="PRESENT", nullable=False),
        sa.Column("late_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "early_leave_minutes", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("note", sa.Text()),
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
            "status IN ('PRESENT', 'LATE', 'ABSENT', 'LEAVE', 'HALF_DAY', 'OT')",
            name="attendance_status",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id", "work_date", name="uq_attendance_employee_work_date"
        ),
    )
    op.create_index("ix_attendance_work_date", "attendance", ["work_date"])
    op.create_index(
        "ix_attendance_employee_work_date",
        "attendance",
        ["employee_id", "work_date"],
    )

    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    bind = op.get_bind()
    existing = set(
        bind.execute(
            sa.select(permissions.c.code).where(
                permissions.c.code.in_(ATTENDANCE_PERMISSION_CODES)
            )
        ).scalars()
    )
    missing = [
        {"id": uuid4(), "code": code}
        for code in ATTENDANCE_PERMISSION_CODES
        if code not in existing
    ]
    if missing:
        bind.execute(permissions.insert(), missing)


def downgrade() -> None:
    permissions = sa.table("permissions", sa.column("code", sa.String()))
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code.in_(ATTENDANCE_PERMISSION_CODES))
    )
    op.drop_index("ix_attendance_employee_work_date", table_name="attendance")
    op.drop_index("ix_attendance_work_date", table_name="attendance")
    op.drop_table("attendance")
