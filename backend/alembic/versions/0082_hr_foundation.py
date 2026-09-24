"""Add HR department and employee foundation.

Revision ID: 0082_hr_foundation
Revises: 0081_pre_generate_video_posters
Create Date: 2026-09-20
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0082_hr_foundation"
down_revision: str | None = "0081_pre_generate_video_posters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HR_PERMISSION_CODES = (
    "hr.departments.manage",
    "hr.employees.read",
    "hr.employees.manage",
    "hr.attendance.self",
    "hr.leave.self",
    "hr.overtime.self",
)


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(8), server_default="ACTIVE", nullable=False),
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
            "status IN ('ACTIVE', 'INACTIVE')", name="department_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "employees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_code", sa.String(32), nullable=False),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.String(160), nullable=False),
        sa.Column(
            "employment_status", sa.String(16), server_default="ACTIVE", nullable=False
        ),
        sa.Column("join_date", sa.Date(), nullable=False),
        sa.Column("contract_type", sa.String(64)),
        sa.Column("base_salary", sa.Numeric(18, 2)),
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
            "employment_status IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED')",
            name="employment_status",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_code"),
    )
    op.create_index("uq_employees_user_id", "employees", ["user_id"], unique=True)
    op.create_index("ix_employees_department_id", "employees", ["department_id"])
    op.create_index("ix_employees_status", "employees", ["employment_status"])

    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    bind = op.get_bind()
    existing = set(
        bind.execute(
            sa.select(permissions.c.code).where(
                permissions.c.code.in_(HR_PERMISSION_CODES)
            )
        ).scalars()
    )
    missing = [
        {"id": uuid4(), "code": code}
        for code in HR_PERMISSION_CODES
        if code not in existing
    ]
    if missing:
        bind.execute(permissions.insert(), missing)


def downgrade() -> None:
    permissions = sa.table("permissions", sa.column("code", sa.String()))
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code.in_(HR_PERMISSION_CODES))
    )
    op.drop_index("ix_employees_status", table_name="employees")
    op.drop_index("ix_employees_department_id", table_name="employees")
    op.drop_index("uq_employees_user_id", table_name="employees")
    op.drop_table("employees")
    op.drop_table("departments")
