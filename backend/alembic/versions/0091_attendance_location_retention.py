"""Enforce 24-month retention for exact attendance coordinates.

Revision ID: 0091_location_retention
Revises: 0090_global_attendance_decisions
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0091_location_retention"
down_revision: str | None = "0090_global_attendance_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("attendance_location_evidence") as batch:
        batch.alter_column(
            "latitude", existing_type=sa.Numeric(precision=9, scale=6), nullable=True
        )
        batch.alter_column(
            "longitude", existing_type=sa.Numeric(precision=9, scale=6), nullable=True
        )
        batch.add_column(sa.Column("retention_until", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("location_purged_at", sa.DateTime(timezone=True)))

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            "UPDATE attendance_location_evidence SET retention_until = "
            "received_at + INTERVAL '24 months'"
        )
    elif dialect == "sqlite":
        op.execute(
            "UPDATE attendance_location_evidence SET retention_until = "
            "datetime(received_at, '+24 months')"
        )
    else:
        op.execute(
            "UPDATE attendance_location_evidence SET retention_until = received_at"
        )

    with op.batch_alter_table("attendance_location_evidence") as batch:
        batch.alter_column("retention_until", nullable=False)
    op.create_index(
        "ix_attendance_location_evidence_retention_until",
        "attendance_location_evidence",
        ["retention_until"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attendance_location_evidence_retention_until",
        table_name="attendance_location_evidence",
    )
    with op.batch_alter_table("attendance_location_evidence") as batch:
        batch.drop_column("location_purged_at")
        batch.drop_column("retention_until")
        batch.alter_column(
            "longitude", existing_type=sa.Numeric(precision=9, scale=6), nullable=False
        )
        batch.alter_column(
            "latitude", existing_type=sa.Numeric(precision=9, scale=6), nullable=False
        )
