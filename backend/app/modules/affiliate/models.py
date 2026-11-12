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
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class AffiliateProfile(UtcTimestampMixin, Base):
    __tablename__ = "affiliate_profiles"
    __table_args__ = (
        CheckConstraint(
            "length(referral_code) BETWEEN 8 AND 32", name="referral_code_length"
        ),
        CheckConstraint(
            "length(short_referral_code) BETWEEN 8 AND 10",
            name="short_referral_code_length",
        ),
        CheckConstraint("status IN ('ACTIVE', 'SUSPENDED')", name="valid_status"),
        Index("ix_affiliate_profiles_status", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    referral_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    short_referral_code: Mapped[str] = mapped_column(
        String(10), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )


class AffiliateReferralCodeAlias(Base):
    __tablename__ = "affiliate_referral_code_aliases"
    __table_args__ = (
        Index("ix_affiliate_referral_code_aliases_owner", "affiliate_user_id"),
    )

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    affiliate_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("affiliate_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AffiliateReferralClick(Base):
    """Deduplicated click event keyed by a client-generated UUID."""

    __tablename__ = "affiliate_referral_clicks"
    __table_args__ = (
        Index(
            "ix_affiliate_referral_clicks_owner_created",
            "affiliate_user_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    affiliate_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("affiliate_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    referral_code_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AffiliateAttribution(Base):
    __tablename__ = "affiliate_attributions"
    __table_args__ = (
        UniqueConstraint("referred_user_id", name="uq_affiliate_attributions_user"),
        CheckConstraint(
            "affiliate_user_id != referred_user_id", name="not_self_referred"
        ),
        CheckConstraint("expires_at > attributed_at", name="valid_window"),
        Index(
            "ix_affiliate_attributions_owner_attributed",
            "affiliate_user_id",
            "attributed_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    affiliate_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("affiliate_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    referred_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    referral_click_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("affiliate_referral_clicks.id", ondelete="SET NULL")
    )
    referral_code_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    attributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AffiliateCommissionRuleSet(UtcTimestampMixin, Base):
    __tablename__ = "affiliate_commission_rule_sets"
    __table_args__ = (
        CheckConstraint("version_no > 0", name="positive_version"),
        CheckConstraint("status IN ('DRAFT', 'PUBLISHED')", name="valid_status"),
        CheckConstraint(
            "attribution_window_days BETWEEN 0 AND 3650",
            name="valid_attribution_window",
        ),
        CheckConstraint("hold_days BETWEEN 0 AND 3650", name="valid_hold_days"),
        CheckConstraint(
            "level2_rate_basis_points BETWEEN 0 AND 10000 AND "
            "((level2_enabled = true AND level2_rate_basis_points > 0) OR "
            "(level2_enabled = false AND level2_rate_basis_points = 0))",
            name="valid_level_two_rate",
        ),
        CheckConstraint(
            "(status = 'PUBLISHED' AND effective_from IS NOT NULL "
            "AND published_at IS NOT NULL) OR status = 'DRAFT'",
            name="published_rule_has_timestamp",
        ),
        Index(
            "ix_affiliate_rule_sets_effective",
            "status",
            "effective_from",
            "version_no",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT", server_default="DRAFT"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    attribution_window_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    hold_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    level2_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    level2_rate_basis_points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )


class AffiliateCommissionRate(Base):
    __tablename__ = "affiliate_commission_rates"
    __table_args__ = (
        UniqueConstraint(
            "rule_set_id", "service_code", name="uq_affiliate_commission_rate_service"
        ),
        CheckConstraint(
            "length(service_code) BETWEEN 1 AND 64", name="service_code_length"
        ),
        CheckConstraint(
            "direct_rate_basis_points BETWEEN 0 AND 10000",
            name="valid_direct_rate",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    rule_set_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("affiliate_commission_rule_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    direct_rate_basis_points: Mapped[int] = mapped_column(Integer, nullable=False)


class AffiliateCommission(Base):
    __tablename__ = "affiliate_commissions"
    __table_args__ = (
        UniqueConstraint("source_reference", name="uq_affiliate_commission_source"),
        CheckConstraint("amount_minor > 0", name="positive_source_amount"),
        CheckConstraint("commission_amount_minor >= 0", name="nonnegative_commission"),
        CheckConstraint("rate_basis_points BETWEEN 0 AND 10000", name="valid_rate"),
        CheckConstraint("commission_level IN (1, 2)", name="valid_commission_level"),
        CheckConstraint(
            "status IN ('PENDING', 'ON_HOLD', 'AVAILABLE', 'REJECTED', 'REVERSED', "
            "'SUPPRESSED')",
            name="valid_status",
        ),
        CheckConstraint(
            "affiliate_user_id != referred_user_id", name="not_self_commission"
        ),
        CheckConstraint(
            "status != 'AVAILABLE' OR finance_journal_id IS NOT NULL",
            name="available_has_journal",
        ),
        CheckConstraint("currency = 'VND'", name="vnd_only"),
        CheckConstraint(
            "status != 'SUPPRESSED' OR commission_amount_minor = 0",
            name="suppressed_has_zero_amount",
        ),
        CheckConstraint(
            "status != 'REVERSED' OR reversed_at IS NOT NULL",
            name="reversed_has_timestamp",
        ),
        Index(
            "ix_affiliate_commissions_owner_status_created",
            "affiliate_user_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_affiliate_commissions_status_hold_until",
            "status",
            "hold_until",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    affiliate_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("affiliate_profiles.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    referred_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    rule_set_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("affiliate_commission_rule_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    commission_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rate_basis_points: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="VND", server_default="VND"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING", server_default="PENDING"
    )
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hold_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    review_reason: Mapped[str | None] = mapped_column(String(1000))
    finance_journal_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("finance_journals.id", ondelete="RESTRICT"),
        unique=True,
    )
    reversal_journal_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("finance_journals.id", ondelete="RESTRICT"),
        unique=True,
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    reversal_reason: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
