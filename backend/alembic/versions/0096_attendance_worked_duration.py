"""Distinguish time capture from credited attendance.

Revision ID: 0096_attendance_worked_duration
Revises: 0095_attendance_work_schedule
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0096_attendance_worked_duration"
down_revision: str | None = "0095_attendance_work_schedule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUSES = (
    "'IN_PROGRESS', 'INCOMPLETE', 'PRESENT', 'LATE', 'ABSENT', 'LEAVE', "
    "'HALF_DAY', 'OT', 'PENDING', 'REJECTED'"
)
_PREVIOUS_STATUSES = (
    "'PRESENT', 'LATE', 'ABSENT', 'LEAVE', 'HALF_DAY', 'OT', 'PENDING', 'REJECTED'"
)
_FULL_DAY_MINUTES = 8 * 60


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def upgrade() -> None:
    with op.batch_alter_table("attendance") as batch:
        batch.drop_constraint("attendance_status", type_="check")
        batch.create_check_constraint("attendance_status", f"status IN ({_STATUSES})")

    attendance = sa.table(
        "attendance",
        sa.column("id", sa.Uuid()),
        sa.column("employee_id", sa.Uuid()),
        sa.column("work_date", sa.Date()),
        sa.column("check_in_at", sa.DateTime(timezone=True)),
        sa.column("check_out_at", sa.DateTime(timezone=True)),
        sa.column("status", sa.String()),
    )
    assignment = sa.table(
        "attendance_assignments",
        sa.column("employee_id", sa.Uuid()),
        sa.column("effective_from", sa.Date()),
        sa.column("effective_to", sa.Date()),
        sa.column("start_time", sa.Time()),
        sa.column("end_time", sa.Time()),
    )
    connection = op.get_bind()
    rows = tuple(
        connection.execute(
            sa.select(attendance).where(
                attendance.c.check_in_at.is_not(None),
                attendance.c.status.in_(("PRESENT", "LATE")),
            )
        ).mappings()
    )
    corrected_count = 0
    for row in rows:
        if row["check_out_at"] is None:
            corrected_status = "IN_PROGRESS"
        else:
            schedule = connection.execute(
                sa.select(assignment.c.start_time, assignment.c.end_time).where(
                    assignment.c.employee_id == row["employee_id"],
                    assignment.c.effective_from <= row["work_date"],
                    sa.or_(
                        assignment.c.effective_to.is_(None),
                        assignment.c.effective_to >= row["work_date"],
                    ),
                )
            ).first()
            required_minutes = _FULL_DAY_MINUTES
            if schedule and schedule.start_time and schedule.end_time:
                span = datetime.combine(date.min, schedule.end_time) - datetime.combine(
                    date.min, schedule.start_time
                )
                required_minutes = min(
                    required_minutes, int(span.total_seconds() // 60)
                )
            worked_minutes = max(
                0,
                int(
                    (
                        _as_utc(row["check_out_at"]) - _as_utc(row["check_in_at"])
                    ).total_seconds()
                    // 60
                ),
            )
            if worked_minutes < (required_minutes + 1) // 2:
                corrected_status = "INCOMPLETE"
            elif worked_minutes < required_minutes:
                corrected_status = "HALF_DAY"
            else:
                continue
        connection.execute(
            sa.update(attendance)
            .where(attendance.c.id == row["id"])
            .values(status=corrected_status)
        )
        corrected_count += 1

    if corrected_count:
        # Cached draft entries may include full credit for the corrected rows.
        # Recalculation is required before a draft can be confirmed.
        connection.execute(
            sa.text(
                "UPDATE payroll_periods SET calculated_at = NULL WHERE status = 'DRAFT'"
            )
        )


def downgrade() -> None:
    op.execute(
        "UPDATE attendance SET status = 'PENDING' "
        "WHERE status IN ('IN_PROGRESS', 'INCOMPLETE')"
    )
    with op.batch_alter_table("attendance") as batch:
        batch.drop_constraint("attendance_status", type_="check")
        batch.create_check_constraint(
            "attendance_status", f"status IN ({_PREVIOUS_STATUSES})"
        )
