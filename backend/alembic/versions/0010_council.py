"""Create council sessions, cases, members, conflicts, and votes.

Revision ID: 0010_council
Revises: 0009_reviews
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_council"
down_revision: str | None = "0009_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SESSION_STATUSES = ("DRAFT", "OPEN", "CLOSED")
VOTE_CHOICES = ("APPROVE", "REJECT", "ABSTAIN", "REQUEST_MORE_INFO")
CASE_DECISIONS = ("APPROVE", "REJECT", "REQUEST_MORE_INFO")


def _enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
    )


def upgrade() -> None:
    op.create_table(
        "council_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            _enum(SESSION_STATUSES, "council_session_status"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("quorum_required", sa.SmallInteger(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("minutes_hash", sa.CHAR(length=64), nullable=True),
        sa.CheckConstraint(
            "quorum_required > 0",
            name="quorum_required_positive",
        ),
        sa.CheckConstraint(
            "minutes_hash IS NULL OR length(minutes_hash) = 64",
            name="minutes_hash_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_council_sessions"),
        sa.UniqueConstraint("code", name="uq_council_sessions_code"),
    )
    op.create_index(
        "ix_council_sessions_status_scheduled_at",
        "council_sessions",
        ["status", "scheduled_at"],
    )

    op.create_table(
        "council_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column(
            "decision",
            _enum(CASE_DECISIONS, "council_case_decision"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["council_sessions.id"],
            name="fk_council_cases_session_id_council_sessions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_council_cases_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"],
            ["dossier_versions.id"],
            name="fk_council_cases_dossier_version_id_dossier_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_council_cases"),
        sa.UniqueConstraint(
            "session_id",
            "dossier_version_id",
            name="uq_council_cases_session_version",
        ),
    )
    op.create_index(
        "ix_council_cases_dossier_id",
        "council_cases",
        ["dossier_id"],
    )

    op.create_table(
        "council_session_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("member_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "attendance_confirmed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["council_sessions.id"],
            name=(
                "fk_council_session_members_session_id_council_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["member_user_id"],
            ["users.id"],
            name="fk_council_session_members_member_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_council_session_members"),
        sa.UniqueConstraint(
            "session_id",
            "member_user_id",
            name="uq_council_session_members_session_member",
        ),
    )
    op.create_index(
        "ix_council_session_members_member_session",
        "council_session_members",
        ["member_user_id", "session_id"],
    )

    op.create_table(
        "council_case_conflicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("member_user_id", sa.Uuid(), nullable=False),
        sa.Column("has_conflict", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "declared_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "(has_conflict AND reason IS NOT NULL "
                "AND length(trim(reason)) > 0) "
                "OR (NOT has_conflict AND reason IS NULL)"
            ),
            name="council_conflict_reason_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["council_cases.id"],
            name="fk_council_case_conflicts_case_id_council_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["member_user_id"],
            ["users.id"],
            name="fk_council_case_conflicts_member_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_council_case_conflicts"),
        sa.UniqueConstraint(
            "case_id",
            "member_user_id",
            name="uq_council_case_conflicts_case_member",
        ),
    )

    op.create_table(
        "council_votes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("member_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "choice",
            _enum(VOTE_CHOICES, "council_vote_choice"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "voted_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 1 AND 2000",
            name="council_vote_reason_length",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["council_cases.id"],
            name="fk_council_votes_case_id_council_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["member_user_id"],
            ["users.id"],
            name="fk_council_votes_member_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_council_votes"),
        sa.UniqueConstraint(
            "case_id",
            "member_user_id",
            name="uq_council_votes_case_member",
        ),
    )


def downgrade() -> None:
    op.drop_table("council_votes")
    op.drop_table("council_case_conflicts")
    op.drop_table("council_session_members")
    op.drop_table("council_cases")
    op.drop_table("council_sessions")
