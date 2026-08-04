"""Create reviewer assignments and 5T scorecards.

Revision ID: 0009_reviews
Revises: 0008_dossier_evidences
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_reviews"
down_revision: str | None = "0008_dossier_evidences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ASSIGNMENT_STATUSES = (
    "ASSIGNED",
    "IN_PROGRESS",
    "CONFLICTED",
    "SUBMITTED",
    "CANCELLED",
)
RECOMMENDATIONS = ("APPROVE", "SUPPLEMENT", "REJECT")


def _enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
    )


def upgrade() -> None:
    op.create_table(
        "review_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            _enum(ASSIGNMENT_STATUSES, "review_assignment_status"),
            nullable=False,
            server_default="ASSIGNED",
        ),
        sa.Column(
            "conflict_declared_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("conflict_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            (
                "status != 'CONFLICTED' OR "
                "(conflict_declared_at IS NOT NULL "
                "AND length(trim(conflict_reason)) > 0)"
            ),
            name="conflicted_reason_required",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_review_assignments_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"],
            ["dossier_versions.id"],
            name=("fk_review_assignments_dossier_version_id_dossier_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["users.id"],
            name="fk_review_assignments_reviewer_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["users.id"],
            name="fk_review_assignments_assigned_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_review_assignments"),
    )
    op.create_index(
        "ix_review_assignments_reviewer_status_due_at",
        "review_assignments",
        ["reviewer_user_id", "status", "due_at"],
    )
    active_condition = sa.text("status IN ('ASSIGNED', 'IN_PROGRESS')")
    op.create_index(
        "uq_review_assignments_active_reviewer_version",
        "review_assignments",
        ["reviewer_user_id", "dossier_version_id"],
        unique=True,
        sqlite_where=active_condition,
        postgresql_where=active_condition,
    )

    comments_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("truth_score", sa.SmallInteger(), nullable=True),
        sa.Column("transparency_score", sa.SmallInteger(), nullable=True),
        sa.Column("ownership_score", sa.SmallInteger(), nullable=True),
        sa.Column("professionalism_score", sa.SmallInteger(), nullable=True),
        sa.Column("respect_score", sa.SmallInteger(), nullable=True),
        sa.Column("total_score", sa.SmallInteger(), nullable=True),
        sa.Column(
            "recommendation",
            _enum(RECOMMENDATIONS, "review_recommendation"),
            nullable=True,
        ),
        sa.Column(
            "criterion_comments",
            comments_type,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("private_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "truth_score BETWEEN 0 AND 20",
            name="truth_score_range",
        ),
        sa.CheckConstraint(
            "transparency_score BETWEEN 0 AND 20",
            name="transparency_score_range",
        ),
        sa.CheckConstraint(
            "ownership_score BETWEEN 0 AND 20",
            name="ownership_score_range",
        ),
        sa.CheckConstraint(
            "professionalism_score BETWEEN 0 AND 20",
            name="professionalism_score_range",
        ),
        sa.CheckConstraint(
            "respect_score BETWEEN 0 AND 20",
            name="respect_score_range",
        ),
        sa.CheckConstraint(
            "total_score BETWEEN 0 AND 100",
            name="total_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["review_assignments.id"],
            name="fk_reviews_assignment_id_review_assignments",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
        sa.UniqueConstraint(
            "assignment_id",
            name="uq_reviews_assignment_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("reviews")
    op.drop_table("review_assignments")
