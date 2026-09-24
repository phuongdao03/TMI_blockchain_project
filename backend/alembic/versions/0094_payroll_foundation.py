"""Add the worksite-month payroll foundation.

Revision ID: 0094_payroll_foundation
Revises: 0093_allocation_review
Create Date: 2026-09-23
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0094_payroll_foundation"
down_revision: str | None = "0093_allocation_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAYROLL_PERMISSION_CODES = (
    "hr.payroll.read",
    "hr.payroll.manage",
)


def upgrade() -> None:
    op.create_table(
        "payroll_periods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worksite_id", sa.Uuid(), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), server_default="VND", nullable=False
        ),
        sa.Column("standard_workdays", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default="DRAFT", nullable=False
        ),
        sa.Column("calculated_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_by_user_id", sa.Uuid()),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("paid_by_user_id", sa.Uuid()),
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
        sa.CheckConstraint("currency = 'VND'", name="payroll_period_currency_vnd"),
        sa.CheckConstraint(
            "standard_workdays >= 1 AND standard_workdays <= 31",
            name="payroll_period_standard_workdays_range",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'PAID')", name="payroll_period_status"
        ),
        sa.ForeignKeyConstraint(
            ["worksite_id"], ["attendance_worksites.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "worksite_id", "period_month", name="uq_payroll_periods_worksite_month"
        ),
    )
    op.create_index(
        "ix_payroll_periods_status_month", "payroll_periods", ["status", "period_month"]
    )
    op.create_table(
        "payroll_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payroll_period_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("employee_code", sa.String(length=32), nullable=False),
        sa.Column("employee_name", sa.String(length=255), nullable=False),
        sa.Column("base_salary", sa.Numeric(precision=18, scale=0), nullable=False),
        sa.Column(
            "attendance_workdays",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "approved_overtime_hours",
            sa.Numeric(precision=7, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "allowance",
            sa.Numeric(precision=18, scale=0),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "social_insurance",
            sa.Numeric(precision=18, scale=0),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "income_tax",
            sa.Numeric(precision=18, scale=0),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "daily_salary",
            sa.Numeric(precision=18, scale=0),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "overtime_salary",
            sa.Numeric(precision=18, scale=0),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "gross_pay",
            sa.Numeric(precision=18, scale=0),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_deductions",
            sa.Numeric(precision=18, scale=0),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "net_pay",
            sa.Numeric(precision=18, scale=0),
            server_default="0",
            nullable=False,
        ),
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
            "base_salary >= 0", name="payroll_entry_base_salary_nonnegative"
        ),
        sa.CheckConstraint(
            "attendance_workdays >= 0", name="payroll_entry_workdays_nonnegative"
        ),
        sa.CheckConstraint(
            "approved_overtime_hours >= 0", name="payroll_entry_overtime_nonnegative"
        ),
        sa.CheckConstraint(
            "allowance >= 0", name="payroll_entry_allowance_nonnegative"
        ),
        sa.CheckConstraint(
            "social_insurance >= 0", name="payroll_entry_social_insurance_nonnegative"
        ),
        sa.CheckConstraint(
            "income_tax >= 0", name="payroll_entry_income_tax_nonnegative"
        ),
        sa.CheckConstraint(
            "daily_salary >= 0", name="payroll_entry_daily_salary_nonnegative"
        ),
        sa.CheckConstraint(
            "overtime_salary >= 0", name="payroll_entry_overtime_salary_nonnegative"
        ),
        sa.CheckConstraint(
            "gross_pay >= 0", name="payroll_entry_gross_pay_nonnegative"
        ),
        sa.CheckConstraint(
            "total_deductions >= 0", name="payroll_entry_total_deductions_nonnegative"
        ),
        sa.CheckConstraint("net_pay >= 0", name="payroll_entry_net_pay_nonnegative"),
        sa.ForeignKeyConstraint(
            ["payroll_period_id"], ["payroll_periods.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payroll_period_id",
            "employee_id",
            name="uq_payroll_entries_period_employee",
        ),
    )
    op.create_index(
        "ix_payroll_entries_employee_period",
        "payroll_entries",
        ["employee_id", "payroll_period_id"],
    )

    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    bind = op.get_bind()
    existing = set(
        bind.execute(
            sa.select(permissions.c.code).where(
                permissions.c.code.in_(PAYROLL_PERMISSION_CODES)
            )
        ).scalars()
    )
    missing = [
        {"id": uuid4(), "code": code}
        for code in PAYROLL_PERMISSION_CODES
        if code not in existing
    ]
    if missing:
        bind.execute(permissions.insert(), missing)


def downgrade() -> None:
    permissions = sa.table("permissions", sa.column("code", sa.String()))
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code.in_(PAYROLL_PERMISSION_CODES))
    )
    op.drop_index("ix_payroll_entries_employee_period", table_name="payroll_entries")
    op.drop_table("payroll_entries")
    op.drop_index("ix_payroll_periods_status_month", table_name="payroll_periods")
    op.drop_table("payroll_periods")
