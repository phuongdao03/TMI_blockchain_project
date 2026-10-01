"""Store actual working days, hours and holiday dates on assignments.

Revision ID: 0095_attendance_work_schedule
Revises: 0094_payroll_foundation
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0095_attendance_work_schedule"
down_revision: str | None = "0094_payroll_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("attendance_assignments", sa.Column("work_days", sa.JSON()))
    op.add_column("attendance_assignments", sa.Column("start_time", sa.Time()))
    op.add_column("attendance_assignments", sa.Column("end_time", sa.Time()))
    op.add_column("attendance_assignments", sa.Column("holiday_dates", sa.JSON()))


def downgrade() -> None:
    op.drop_column("attendance_assignments", "holiday_dates")
    op.drop_column("attendance_assignments", "end_time")
    op.drop_column("attendance_assignments", "start_time")
    op.drop_column("attendance_assignments", "work_days")
