from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class CommunityEvent(UtcTimestampMixin, Base):
    __tablename__ = "community_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'CANCELLED')", name="valid_status"
        ),
        CheckConstraint(
            "required_tier IN ('MEMBER', 'SILVER', 'COMPANION', 'PRESTIGE')",
            name="valid_required_tier",
        ),
        CheckConstraint(
            "included_entitlement IS NULL OR included_entitlement IN "
            "('TALK', 'CONNECT', 'CIRCLE')",
            name="valid_included_entitlement",
        ),
        CheckConstraint("capacity >= 1", name="positive_capacity"),
        CheckConstraint(
            "confirmed_count >= 0 AND confirmed_count <= capacity",
            name="valid_confirmed_count",
        ),
        CheckConstraint(
            "ticket_price_minor >= 0 AND ticket_price_minor <= 1000000000",
            name="valid_ticket_price",
        ),
        CheckConstraint(
            "(included_entitlement IS NULL AND entitlement_quota IS NULL) "
            "OR (included_entitlement IS NOT NULL AND entitlement_quota >= 1)",
            name="valid_entitlement_quota",
        ),
        CheckConstraint(
            "NOT requires_diamond_approval OR required_tier = 'PRESTIGE'",
            name="diamond_circle_tier",
        ),
        CheckConstraint(
            "included_entitlement != 'CIRCLE' OR "
            "(required_tier = 'PRESTIGE' AND requires_diamond_approval)",
            name="circle_requires_diamond_approval",
        ),
        CheckConstraint("ends_at > starts_at", name="valid_event_window"),
        CheckConstraint(
            "priority_tier IS NULL OR priority_tier IN ('COMPANION', 'PRESTIGE')",
            name="valid_priority_tier",
        ),
        CheckConstraint(
            "cancellation_cutoff_at IS NULL OR cancellation_cutoff_at <= starts_at",
            name="valid_cancellation_cutoff",
        ),
        Index("ix_community_events_status_starts", "status", "starts_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_opens_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    priority_tier: Mapped[str | None] = mapped_column(String(16))
    priority_opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(String(300), nullable=False)
    required_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ticket_price_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    cancellation_cutoff_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    included_entitlement: Mapped[str | None] = mapped_column(String(16))
    entitlement_quota: Mapped[int | None] = mapped_column(Integer)
    requires_diamond_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class CommunityEventRegistration(Base):
    __tablename__ = "community_event_registrations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CONFIRMED', 'WAITLISTED', 'CANCELLED', "
            "'CANCELLED_LATE', 'CANCELLED_BY_EVENT', 'INELIGIBLE', "
            "'PAYMENT_REQUIRED')",
            name="valid_status",
        ),
        CheckConstraint(
            "(entitlement_units = 0 AND entitlement_snapshot IS NULL "
            "AND entitlement_cycle_started_at IS NULL "
            "AND membership_tier_snapshot IS NULL) "
            "OR (entitlement_units > 0 AND entitlement_snapshot IS NOT NULL "
            "AND entitlement_cycle_started_at IS NOT NULL "
            "AND membership_tier_snapshot IS NOT NULL)",
            name="valid_entitlement_snapshot",
        ),
        Index(
            "uq_community_event_registrations_active_user_event",
            "event_id",
            "user_id",
            unique=True,
            sqlite_where=text("status IN ('CONFIRMED', 'WAITLISTED')"),
            postgresql_where=text("status IN ('CONFIRMED', 'WAITLISTED')"),
        ),
        Index(
            "ix_community_event_registrations_event_waitlist",
            "event_id",
            "status",
            "registered_at",
        ),
        Index(
            "ix_community_event_registrations_user_registered",
            "user_id",
            "registered_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("community_events.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    entitlement_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entitlement_snapshot: Mapped[str | None] = mapped_column(String(16))
    entitlement_cycle_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    membership_tier_snapshot: Mapped[str | None] = mapped_column(String(16))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MembershipEventEntitlementPolicy(Base):
    __tablename__ = "membership_event_entitlement_policies"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('SILVER', 'COMPANION', 'PRESTIGE')", name="valid_tier"
        ),
        CheckConstraint(
            "entitlement IN ('TALK', 'CONNECT', 'CIRCLE')", name="valid_entitlement"
        ),
        CheckConstraint("quota_count >= 1", name="positive_quota"),
    )

    tier: Mapped[str] = mapped_column(String(16), primary_key=True)
    entitlement: Mapped[str] = mapped_column(String(16), primary_key=True)
    quota_count: Mapped[int] = mapped_column(Integer, nullable=False)


class MembershipEventEntitlementUsage(Base):
    __tablename__ = "membership_event_entitlement_usage"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('SILVER', 'COMPANION', 'PRESTIGE')", name="valid_tier"
        ),
        CheckConstraint(
            "entitlement IN ('TALK', 'CONNECT', 'CIRCLE')", name="valid_entitlement"
        ),
        CheckConstraint("used_count >= 0", name="nonnegative_used_count"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    tier: Mapped[str] = mapped_column(String(16), primary_key=True)
    entitlement: Mapped[str] = mapped_column(String(16), primary_key=True)
    cycle_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
