"""Add dossier review assistance requests.

Revision ID: 0087_review_assistance
Revises: 0086_task_foundation
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0087_review_assistance"
down_revision: str | None = "0086_task_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_assistance_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_reviewer_count", sa.SmallInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), server_default="PENDING", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid()),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'DECLINED')",
            name="review_assistance_request_status",
        ),
        sa.CheckConstraint(
            "requested_reviewer_count BETWEEN 1 AND 10",
            name="assistance_requested_reviewer_count",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 20 AND 2000",
            name="assistance_reason_length",
        ),
        sa.CheckConstraint(
            "(status = 'PENDING' AND reviewed_by_user_id IS NULL "
            "AND reviewed_at IS NULL AND decision_reason IS NULL) OR "
            "(status = 'APPROVED' AND reviewed_by_user_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL) OR "
            "(status = 'DECLINED' AND reviewed_by_user_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL "
            "AND length(trim(decision_reason)) BETWEEN 20 AND 2000)",
            name="assistance_request_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["review_assignments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_review_assistance_requests_pending_assignment",
        "review_assistance_requests",
        ["assignment_id"],
        unique=True,
        sqlite_where=sa.text("status = 'PENDING'"),
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        "ix_review_assistance_requests_status_created",
        "review_assistance_requests",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_review_assistance_requests_status_created",
        table_name="review_assistance_requests",
    )
    op.drop_index(
        "uq_review_assistance_requests_pending_assignment",
        table_name="review_assistance_requests",
    )
    op.drop_table("review_assistance_requests")
