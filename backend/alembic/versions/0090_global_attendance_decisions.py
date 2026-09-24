"""Add global attendance exception decisions.

Revision ID: 0090_global_attendance_decisions
Revises: 0089_global_attendance_admin
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0090_global_attendance_decisions"
down_revision: str | None = "0089_global_attendance_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_ATTENDANCE_STATUSES = (
    "'PRESENT', 'LATE', 'ABSENT', 'LEAVE', 'HALF_DAY', 'OT', 'PENDING', 'REJECTED'"
)
_LEGACY_ATTENDANCE_STATUSES = "'PRESENT', 'LATE', 'ABSENT', 'LEAVE', 'HALF_DAY', 'OT'"


def upgrade() -> None:
    with op.batch_alter_table("attendance") as batch:
        batch.drop_constraint("attendance_status", type_="check")
        batch.create_check_constraint(
            "attendance_status", f"status IN ({_CURRENT_ATTENDANCE_STATUSES})"
        )

    op.create_table(
        "attendance_location_exceptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attendance_id", sa.Uuid(), nullable=False),
        sa.Column("location_evidence_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default="PENDING", nullable=False
        ),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
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
            "status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="location_exception_status",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_id"], ["attendance.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["location_evidence_id"],
            ["attendance_location_evidence.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_attendance_location_exceptions_evidence",
        "attendance_location_exceptions",
        ["location_evidence_id"],
        unique=True,
    )
    op.create_index(
        "ix_attendance_location_exceptions_status_created",
        "attendance_location_exceptions",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attendance_location_exceptions_status_created",
        table_name="attendance_location_exceptions",
    )
    op.drop_index(
        "uq_attendance_location_exceptions_evidence",
        table_name="attendance_location_exceptions",
    )
    op.drop_table("attendance_location_exceptions")
    op.execute(
        "UPDATE attendance SET status = 'ABSENT' "
        "WHERE status IN ('PENDING', 'REJECTED')"
    )
    with op.batch_alter_table("attendance") as batch:
        batch.drop_constraint("attendance_status", type_="check")
        batch.create_check_constraint(
            "attendance_status", f"status IN ({_LEGACY_ATTENDANCE_STATUSES})"
        )
