from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, UtcTimestampMixin


class CampaignStatus(StrEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ENDED = "ENDED"
    RESULT_PENDING = "RESULT_PENDING"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class CampaignType(StrEnum):
    PERIODIC = "PERIODIC"
    SPECIAL = "SPECIAL"


class PeriodType(StrEnum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    CUSTOM = "CUSTOM"


class CampaignWorkStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REMOVED = "REMOVED"


class VoteStatus(StrEnum):
    VALID = "VALID"
    SUSPICIOUS = "SUSPICIOUS"
    REVOKED_BY_USER = "REVOKED_BY_USER"
    INVALIDATED = "INVALIDATED"
    REJECTED = "REJECTED"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=True,
        create_constraint=True,
        values_callable=lambda values: [value.value for value in values],
        validate_strings=True,
    )


VOTING_JSON = JSONB().with_variant(JSON(), "sqlite")


class VotingCampaign(UtcTimestampMixin, Base):
    __tablename__ = "voting_campaigns"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="time_window_valid"),
        CheckConstraint(
            "max_votes_per_user > 0",
            name="max_votes_per_user_positive",
        ),
        CheckConstraint(
            "max_votes_per_work_per_user = 1",
            name="max_votes_per_work_one",
        ),
        CheckConstraint(
            "min_account_age_hours >= 0",
            name="min_account_age_non_negative",
        ),
        CheckConstraint("rule_version > 0", name="rule_version_positive"),
        CheckConstraint(
            "(campaign_type = 'SPECIAL' AND period_type = 'CUSTOM') "
            "OR (campaign_type = 'PERIODIC' AND period_type != 'CUSTOM')",
            name="classification_consistent",
        ),
        Index(
            "ix_voting_campaigns_status_window",
            "status",
            "start_at",
            "end_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        _enum(CampaignStatus, "voting_campaign_status"),
        nullable=False,
        default=CampaignStatus.DRAFT,
        server_default=CampaignStatus.DRAFT.value,
    )
    campaign_type: Mapped[CampaignType] = mapped_column(
        _enum(CampaignType, "voting_campaign_type"),
        nullable=False,
    )
    period_type: Mapped[PeriodType] = mapped_column(
        _enum(PeriodType, "voting_period_type"),
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_votes_per_user: Mapped[int] = mapped_column(Integer, nullable=False)
    max_votes_per_work_per_user: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    allow_vote_change: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    allow_vote_revoke: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    require_verified_email: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    min_account_age_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    eligibility_rules: Mapped[dict[str, object]] = mapped_column(
        VOTING_JSON,
        nullable=False,
        default=dict,
    )
    rule_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    published_snapshot_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ranking_snapshots.id", ondelete="RESTRICT"),
    )
    results_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )


class CampaignWork(UtcTimestampMixin, Base):
    __tablename__ = "campaign_works"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "work_id",
            name="uq_campaign_works_campaign_work",
        ),
        CheckConstraint(
            "(status = 'APPROVED' AND approved_by IS NOT NULL "
            "AND approved_at IS NOT NULL) OR status != 'APPROVED'",
            name="approval_consistent",
        ),
        Index("ix_campaign_works_work_status", "work_id", "status"),
        Index("ix_campaign_works_campaign_status", "campaign_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("voting_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[CampaignWorkStatus] = mapped_column(
        _enum(CampaignWorkStatus, "campaign_work_status"),
        nullable=False,
        default=CampaignWorkStatus.PENDING,
        server_default=CampaignWorkStatus.PENDING.value,
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        VOTING_JSON,
        nullable=False,
        default=dict,
    )


class Vote(UtcTimestampMixin, Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_votes_user_idempotency",
        ),
        CheckConstraint("risk_score >= 0", name="risk_score_non_negative"),
        CheckConstraint(
            "(status = 'REVOKED_BY_USER' AND revoked_at IS NOT NULL) "
            "OR (status != 'REVOKED_BY_USER' AND revoked_at IS NULL)",
            name="revoked_at_consistent",
        ),
        Index(
            "uq_votes_effective_campaign_work_user",
            "campaign_id",
            "work_id",
            "user_id",
            unique=True,
            sqlite_where=text("status IN ('VALID', 'SUSPICIOUS')"),
            postgresql_where=text("status IN ('VALID', 'SUSPICIOUS')"),
        ),
        Index(
            "ix_votes_campaign_work_status",
            "campaign_id",
            "work_id",
            "status",
        ),
        Index("ix_votes_user_campaign", "user_id", "campaign_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("voting_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[VoteStatus] = mapped_column(
        _enum(VoteStatus, "vote_status"),
        nullable=False,
        default=VoteStatus.VALID,
        server_default=VoteStatus.VALID.value,
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VoteAggregate(Base):
    __tablename__ = "vote_aggregates"
    __table_args__ = (
        CheckConstraint("effective_count >= 0", name="effective_count_non_negative"),
        Index("ix_vote_aggregates_campaign_count", "campaign_id", "effective_count"),
    )

    campaign_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("voting_campaigns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="CASCADE"),
        primary_key=True,
    )
    effective_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1,
        server_default="1",
    )
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class VoteEvent(Base):
    __tablename__ = "vote_events"
    __table_args__ = (Index("ix_vote_events_vote_created", "vote_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    vote_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("votes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        VOTING_JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class CampaignEvent(Base):
    __tablename__ = "campaign_events"
    __table_args__ = (
        Index("ix_campaign_events_campaign_created", "campaign_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("voting_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    before_snapshot: Mapped[dict[str, object] | None] = mapped_column(VOTING_JSON)
    after_snapshot: Mapped[dict[str, object] | None] = mapped_column(VOTING_JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
