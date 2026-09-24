"""Bridge work-allocation scopes to authoritative review assignments.

Revision ID: 0093_allocation_review
Revises: 0092_work_allocation_foundation
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0093_allocation_review"
down_revision: str | None = "0092_work_allocation_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_scope_review_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("allocation_member_id", sa.Uuid(), nullable=False),
        sa.Column("review_assignment_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["scope_id"], ["work_scopes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["allocation_member_id"],
            ["allocation_members.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["review_assignment_id"],
            ["review_assignments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope_id",
            "review_assignment_id",
            name="uq_work_scope_review_assignments_scope_review_assignment",
        ),
    )
    op.create_index(
        "ix_work_scope_review_assignments_scope",
        "work_scope_review_assignments",
        ["scope_id"],
    )
    op.create_index(
        "ix_work_scope_review_assignments_review_assignment",
        "work_scope_review_assignments",
        ["review_assignment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_work_scope_review_assignments_review_assignment",
        table_name="work_scope_review_assignments",
    )
    op.drop_index(
        "ix_work_scope_review_assignments_scope",
        table_name="work_scope_review_assignments",
    )
    op.drop_table("work_scope_review_assignments")
