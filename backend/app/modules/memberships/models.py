from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MembershipPlan(Base):
    __tablename__ = "membership_plans"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('SILVER', 'COMPANION', 'PRESTIGE')", name="valid_tier"
        ),
        CheckConstraint(
            "amount_minor > 0 AND amount_minor <= 1000000000", name="amount_range"
        ),
        CheckConstraint("duration_days BETWEEN 1 AND 3660", name="duration_range"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    benefits: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    conditions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserMembership(Base):
    __tablename__ = "user_memberships"
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    plan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("membership_plans.id", ondelete="RESTRICT"), nullable=False
    )
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class MembershipPurchase(Base):
    __tablename__ = "membership_purchases"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="positive_amount"),
        CheckConstraint(
            "list_price_minor >= amount_minor AND credit_minor >= 0",
            name="valid_price_snapshot",
        ),
        Index(
            "ix_membership_purchases_owner_tier_expiry",
            "user_id",
            "tier",
            "expires_at",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("wallet_journals.id", ondelete="RESTRICT"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    plan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("membership_plans.id", ondelete="RESTRICT")
    )
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    list_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    credit_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MembershipDiamondApplication(Base):
    __tablename__ = "membership_diamond_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'INFO_REQUESTED', 'APPROVED', 'REJECTED')",
            name="valid_status",
        ),
        CheckConstraint(
            "length(trim(statement)) BETWEEN 1 AND 5000", name="statement_length"
        ),
        CheckConstraint(
            "decision_note IS NULL OR length(trim(decision_note)) <= 2000",
            name="decision_note_length",
        ),
        Index(
            "uq_membership_diamond_applications_open_user",
            "user_id",
            unique=True,
            sqlite_where=text("status IN ('PENDING', 'INFO_REQUESTED')"),
            postgresql_where=text("status IN ('PENDING', 'INFO_REQUESTED')"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    decision_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CommunityChatMessage(Base):
    __tablename__ = "community_chat_messages"
    __table_args__ = (
        CheckConstraint(
            "room IN ('MEMBER', 'COMPANION', 'PRESTIGE')", name="valid_room"
        ),
        CheckConstraint("length(trim(body)) BETWEEN 1 AND 2000", name="body_length"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    room: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tier_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MembershipChatRoomAccess(Base):
    __tablename__ = "membership_chat_room_access"
    __table_args__ = (
        CheckConstraint(
            "room IN ('MEMBER', 'COMPANION', 'PRESTIGE')", name="valid_room"
        ),
        CheckConstraint(
            "length(trim(reason)) BETWEEN 3 AND 240", name="valid_reason"
        ),
        Index("ix_membership_chat_room_access_room", "room"),
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    room: Mapped[str] = mapped_column(String(16), primary_key=True)
    granted_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MembershipBenefitRequest(Base):
    __tablename__ = "membership_benefit_requests"
    __table_args__ = (
        CheckConstraint(
            "benefit IN ('COLLABORATION_NEED', 'ADVISORY_SESSION', "
            "'FACILITATED_INTRODUCTION', 'MEMBER_STORY')",
            name="valid_benefit",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'INFO_REQUESTED', 'APPROVED', "
            "'COMPLETED', 'REJECTED')",
            name="valid_status",
        ),
        CheckConstraint(
            "length(trim(statement)) BETWEEN 1 AND 5000",
            name="statement_length",
        ),
        CheckConstraint(
            "decision_note IS NULL OR length(trim(decision_note)) <= 2000",
            name="decision_note_length",
        ),
        Index(
            "ix_membership_benefit_requests_owner_cycle",
            "user_id",
            "benefit",
            "cycle_started_at",
        ),
        Index(
            "ix_membership_benefit_requests_queue",
            "status",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    benefit: Mapped[str] = mapped_column(String(32), nullable=False)
    cycle_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    decision_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
