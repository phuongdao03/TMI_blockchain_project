"""Add global attendance location foundation.

Revision ID: 0088_global_attendance
Revises: 0087_review_assistance
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0088_global_attendance"
down_revision: str | None = "0087_review_assistance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attendance_worksites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default="ACTIVE", nullable=False
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
            "status IN ('ACTIVE', 'INACTIVE')",
            name="attendance_worksite_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "attendance_worksite_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worksite_id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("radius_meters", sa.Integer(), nullable=False),
        sa.Column("max_accuracy_meters", sa.Integer(), nullable=False),
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
            "effective_to IS NULL OR effective_to >= effective_from",
            name="attendance_worksite_policy_effective_range",
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="attendance_worksite_policy_latitude",
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="attendance_worksite_policy_longitude",
        ),
        sa.CheckConstraint(
            "radius_meters > 0",
            name="attendance_worksite_policy_radius_positive",
        ),
        sa.CheckConstraint(
            "max_accuracy_meters > 0",
            name="attendance_worksite_policy_accuracy_positive",
        ),
        sa.ForeignKeyConstraint(
            ["worksite_id"], ["attendance_worksites.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worksite_id", "effective_from"),
    )
    op.create_index(
        "ix_attendance_worksite_policies_worksite_effective",
        "attendance_worksite_policies",
        ["worksite_id", "effective_from"],
    )

    op.create_table(
        "attendance_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("worksite_id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        sa.Column("schedule_code", sa.String(length=64), nullable=False),
        sa.Column("holiday_calendar_code", sa.String(length=64), nullable=False),
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
            "effective_to IS NULL OR effective_to >= effective_from",
            name="attendance_assignment_effective_range",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["worksite_id"], ["attendance_worksites.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "effective_from"),
    )
    op.create_index(
        "ix_attendance_assignments_employee_effective",
        "attendance_assignments",
        ["employee_id", "effective_from"],
    )

    op.create_table(
        "attendance_location_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attendance_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("worksite_policy_id", sa.Uuid(), nullable=False),
        sa.Column("client_captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("accuracy_meters", sa.Numeric(8, 2), nullable=False),
        sa.Column("distance_meters", sa.Numeric(10, 2), nullable=False),
        sa.Column("effective_timezone", sa.String(length=64), nullable=False),
        sa.Column("permitted_radius_meters", sa.Integer(), nullable=False),
        sa.Column("max_accuracy_meters", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
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
            "event_type IN ('CHECK_IN', 'CHECK_OUT')",
            name="location_evidence_event_type",
        ),
        sa.CheckConstraint(
            "outcome IN ('ACCEPTED', 'OUTSIDE_WORKSITE', 'LOW_ACCURACY', "
            "'LOCATION_UNAVAILABLE', 'EXCEPTION_APPROVED')",
            name="location_evidence_outcome",
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="location_evidence_latitude",
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="location_evidence_longitude",
        ),
        sa.CheckConstraint(
            "accuracy_meters > 0",
            name="location_evidence_accuracy_positive",
        ),
        sa.CheckConstraint(
            "distance_meters >= 0",
            name="location_evidence_distance_nonnegative",
        ),
        sa.CheckConstraint(
            "permitted_radius_meters > 0",
            name="location_evidence_radius_positive",
        ),
        sa.CheckConstraint(
            "max_accuracy_meters > 0",
            name="location_evidence_max_accuracy_positive",
        ),
        sa.ForeignKeyConstraint(
            ["attendance_id"], ["attendance.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["worksite_policy_id"],
            ["attendance_worksite_policies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_attendance_location_evidence_attendance_event",
        "attendance_location_evidence",
        ["attendance_id", "event_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_attendance_location_evidence_attendance_event",
        table_name="attendance_location_evidence",
    )
    op.drop_table("attendance_location_evidence")
    op.drop_index(
        "ix_attendance_assignments_employee_effective",
        table_name="attendance_assignments",
    )
    op.drop_table("attendance_assignments")
    op.drop_index(
        "ix_attendance_worksite_policies_worksite_effective",
        table_name="attendance_worksite_policies",
    )
    op.drop_table("attendance_worksite_policies")
    op.drop_table("attendance_worksites")
