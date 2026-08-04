"""Create voting campaigns, participants, votes, and append-only events.

Revision ID: 0022_voting_foundation
Revises: 0021_search_discovery
Create Date: 2026-08-03
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0022_voting_foundation"
down_revision: str | None = "0021_search_discovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CAMPAIGN_STATUSES = (
    "DRAFT",
    "SCHEDULED",
    "ACTIVE",
    "PAUSED",
    "ENDED",
    "RESULT_PENDING",
    "PUBLISHED",
    "CANCELLED",
)
CAMPAIGN_TYPES = ("PERIODIC", "SPECIAL")
PERIOD_TYPES = ("MONTHLY", "QUARTERLY", "YEARLY", "CUSTOM")
CAMPAIGN_WORK_STATUSES = ("PENDING", "APPROVED", "REMOVED")
VOTE_STATUSES = (
    "VALID",
    "SUSPICIOUS",
    "REVOKED_BY_USER",
    "INVALIDATED",
    "REJECTED",
)

POSTGRES_ENUMS = (
    postgresql.ENUM(
        *CAMPAIGN_STATUSES,
        name="voting_campaign_status",
        create_type=False,
    ),
    postgresql.ENUM(
        *CAMPAIGN_TYPES,
        name="voting_campaign_type",
        create_type=False,
    ),
    postgresql.ENUM(
        *PERIOD_TYPES,
        name="voting_period_type",
        create_type=False,
    ),
    postgresql.ENUM(
        *CAMPAIGN_WORK_STATUSES,
        name="campaign_work_status",
        create_type=False,
    ),
    postgresql.ENUM(*VOTE_STATUSES, name="vote_status", create_type=False),
)


def _enum(
    values: tuple[str, ...],
    name: str,
    *,
    is_postgresql: bool,
) -> sa.types.TypeEngine[str]:
    if is_postgresql:
        return next(enum for enum in POSTGRES_ENUMS if enum.name == name)
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
    )


def _timestamps() -> tuple[sa.Column[datetime], sa.Column[datetime]]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"
    if is_postgresql:
        for enum in POSTGRES_ENUMS:
            enum.create(bind, checkfirst=True)
    json_type: sa.types.TypeEngine[object] = JSONB() if is_postgresql else sa.JSON()

    op.create_table(
        "voting_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            _enum(
                CAMPAIGN_STATUSES,
                "voting_campaign_status",
                is_postgresql=is_postgresql,
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "campaign_type",
            _enum(
                CAMPAIGN_TYPES,
                "voting_campaign_type",
                is_postgresql=is_postgresql,
            ),
            nullable=False,
        ),
        sa.Column(
            "period_type",
            _enum(
                PERIOD_TYPES,
                "voting_period_type",
                is_postgresql=is_postgresql,
            ),
            nullable=False,
        ),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_votes_per_user", sa.Integer(), nullable=False),
        sa.Column(
            "max_votes_per_work_per_user",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "allow_vote_change",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "allow_vote_revoke",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "require_verified_email",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "min_account_age_hours",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("eligibility_rules", json_type, nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("end_at > start_at", name="time_window_valid"),
        sa.CheckConstraint(
            "max_votes_per_user > 0", name="max_votes_per_user_positive"
        ),
        sa.CheckConstraint(
            "max_votes_per_work_per_user = 1", name="max_votes_per_work_one"
        ),
        sa.CheckConstraint(
            "min_account_age_hours >= 0", name="min_account_age_non_negative"
        ),
        sa.CheckConstraint("rule_version > 0", name="rule_version_positive"),
        sa.CheckConstraint(
            "(campaign_type = 'SPECIAL' AND period_type = 'CUSTOM') "
            "OR (campaign_type = 'PERIODIC' AND period_type != 'CUSTOM')",
            name="classification_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_voting_campaigns_created_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_voting_campaigns"),
        sa.UniqueConstraint("slug", name="uq_voting_campaigns_slug"),
    )
    op.create_index(
        "ix_voting_campaigns_status_window",
        "voting_campaigns",
        ["status", "start_at", "end_at"],
    )

    op.create_table(
        "campaign_works",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            _enum(
                CAMPAIGN_WORK_STATUSES,
                "campaign_work_status",
                is_postgresql=is_postgresql,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("approved_by", sa.Uuid()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", json_type, nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "(status = 'APPROVED' AND approved_by IS NOT NULL "
            "AND approved_at IS NOT NULL) OR status != 'APPROVED'",
            name="approval_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["voting_campaigns.id"],
            name="fk_campaign_works_campaign_id_voting_campaigns",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["public_works.id"],
            name="fk_campaign_works_work_id_public_works",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_campaign_works_approved_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_campaign_works"),
        sa.UniqueConstraint(
            "campaign_id",
            "work_id",
            name="uq_campaign_works_campaign_work",
        ),
    )
    op.create_index(
        "ix_campaign_works_work_status", "campaign_works", ["work_id", "status"]
    )
    op.create_index(
        "ix_campaign_works_campaign_status",
        "campaign_works",
        ["campaign_id", "status"],
    )

    op.create_table(
        "votes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            _enum(VOTE_STATUSES, "vote_status", is_postgresql=is_postgresql),
            nullable=False,
            server_default="VALID",
        ),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column(
            "risk_score",
            sa.Numeric(8, 4),
            nullable=False,
            server_default="0",
        ),
        *_timestamps(),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("risk_score >= 0", name="risk_score_non_negative"),
        sa.CheckConstraint(
            "(status = 'REVOKED_BY_USER' AND revoked_at IS NOT NULL) "
            "OR (status != 'REVOKED_BY_USER' AND revoked_at IS NULL)",
            name="revoked_at_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["voting_campaigns.id"],
            name="fk_votes_campaign_id_voting_campaigns",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["public_works.id"],
            name="fk_votes_work_id_public_works",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_votes_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_votes"),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_votes_user_idempotency",
        ),
    )
    effective_condition = sa.text("status IN ('VALID', 'SUSPICIOUS')")
    op.create_index(
        "uq_votes_effective_campaign_work_user",
        "votes",
        ["campaign_id", "work_id", "user_id"],
        unique=True,
        sqlite_where=effective_condition,
        postgresql_where=effective_condition,
    )
    op.create_index(
        "ix_votes_campaign_work_status",
        "votes",
        ["campaign_id", "work_id", "status"],
    )
    op.create_index(
        "ix_votes_user_campaign",
        "votes",
        ["user_id", "campaign_id", "created_at"],
    )

    op.create_table(
        "vote_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vote_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid()),
        sa.Column("reason", sa.String(500)),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["vote_id"],
            ["votes.id"],
            name="fk_vote_events_vote_id_votes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_vote_events_actor_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vote_events"),
    )
    op.create_index(
        "ix_vote_events_vote_created", "vote_events", ["vote_id", "created_at"]
    )

    op.create_table(
        "campaign_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid()),
        sa.Column("reason", sa.String(500)),
        sa.Column("before_snapshot", json_type),
        sa.Column("after_snapshot", json_type),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["voting_campaigns.id"],
            name="fk_campaign_events_campaign_id_voting_campaigns",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_campaign_events_actor_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_campaign_events"),
    )
    op.create_index(
        "ix_campaign_events_campaign_created",
        "campaign_events",
        ["campaign_id", "created_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_campaign_events_campaign_created", table_name="campaign_events")
    op.drop_table("campaign_events")
    op.drop_index("ix_vote_events_vote_created", table_name="vote_events")
    op.drop_table("vote_events")
    op.drop_index("ix_votes_user_campaign", table_name="votes")
    op.drop_index("ix_votes_campaign_work_status", table_name="votes")
    op.drop_index("uq_votes_effective_campaign_work_user", table_name="votes")
    op.drop_table("votes")
    op.drop_index("ix_campaign_works_campaign_status", table_name="campaign_works")
    op.drop_index("ix_campaign_works_work_status", table_name="campaign_works")
    op.drop_table("campaign_works")
    op.drop_index("ix_voting_campaigns_status_window", table_name="voting_campaigns")
    op.drop_table("voting_campaigns")
    if bind.dialect.name == "postgresql":
        for enum in reversed(POSTGRES_ENUMS):
            enum.drop(bind, checkfirst=True)
