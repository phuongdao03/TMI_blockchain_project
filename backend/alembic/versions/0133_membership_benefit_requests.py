"""Add member benefit fulfillment requests.

Revision ID: 0133_membership_benefit_requests
Revises: 0132_membership_catalog_content
"""

import sqlalchemy as sa

from alembic import op

revision = "0133_membership_benefit_requests"
down_revision = "0132_membership_catalog_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "membership_benefit_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("benefit", sa.String(length=32), nullable=False),
        sa.Column("cycle_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
            "benefit IN ('COLLABORATION_NEED', 'ADVISORY_SESSION', "
            "'FACILITATED_INTRODUCTION', 'MEMBER_STORY')",
            name="valid_benefit",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'INFO_REQUESTED', 'APPROVED', "
            "'COMPLETED', 'REJECTED')",
            name="valid_status",
        ),
        sa.CheckConstraint(
            "length(trim(statement)) BETWEEN 1 AND 5000",
            name="statement_length",
        ),
        sa.CheckConstraint(
            "decision_note IS NULL OR length(trim(decision_note)) <= 2000",
            name="decision_note_length",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_membership_benefit_requests_owner_cycle",
        "membership_benefit_requests",
        ["user_id", "benefit", "cycle_started_at"],
    )
    op.create_index(
        "ix_membership_benefit_requests_queue",
        "membership_benefit_requests",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_membership_benefit_requests_queue",
        table_name="membership_benefit_requests",
    )
    op.drop_index(
        "ix_membership_benefit_requests_owner_cycle",
        table_name="membership_benefit_requests",
    )
    op.drop_table("membership_benefit_requests")
