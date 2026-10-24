from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class AdvertisingPlacement(UtcTimestampMixin, Base):
    __tablename__ = "advertising_placements"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="capacity_positive"),
        CheckConstraint(
            "delivery_mode IN ('EQUAL_ROTATION', 'WEIGHTED_ROTATION', 'EXCLUSIVE')",
            name="valid_delivery_mode",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    page_location: Mapped[str] = mapped_column(String(160), nullable=False)
    delivery_mode: Mapped[str] = mapped_column(
        String(24), nullable=False, default="EQUAL_ROTATION"
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Asia/Bangkok",
        server_default="Asia/Bangkok",
    )
    rotation_pool_key: Mapped[str | None] = mapped_column(String(64))


class AdvertisingPackage(UtcTimestampMixin, Base):
    __tablename__ = "advertising_packages"
    __table_args__ = (
        CheckConstraint("duration_hours > 0", name="duration_positive"),
        CheckConstraint("base_price_vnd >= 0", name="price_nonnegative"),
        CheckConstraint("price_version > 0", name="price_version_positive"),
        CheckConstraint(
            "rotation_weight BETWEEN 1 AND 100", name="valid_rotation_weight"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    placement_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(AdvertisingPlacement.id, ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    rotation_weight: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    base_price_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    terms: Mapped[str] = mapped_column(Text, nullable=False, default="")


class AdvertisingCampaign(UtcTimestampMixin, Base):
    __tablename__ = "advertising_campaigns"
    __table_args__ = (
        CheckConstraint(
            "purchase_context IN ('BEFORE_PUBLICATION', 'AFTER_PUBLICATION')",
            name="valid_purchase_context",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'PENDING_PAYMENT', "
            "'SCHEDULED', 'NEEDS_RESCHEDULE', 'ACTIVE', 'PAUSED', 'COMPLETED', "
            "'CANCELLED', 'REJECTED')",
            name="valid_status",
        ),
        CheckConstraint(
            "rotation_weight BETWEEN 1 AND 100", name="valid_rotation_weight"
        ),
        CheckConstraint("delivery_count >= 0", name="delivery_count_nonnegative"),
        CheckConstraint("rotation_count >= 0", name="rotation_count_nonnegative"),
        Index("ix_advertising_campaigns_owner_created", "owner_user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False
    )
    package_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingPackage.id, ondelete="RESTRICT"), nullable=False
    )
    placement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingPlacement.id, ondelete="RESTRICT"), nullable=False
    )
    purchase_context: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="DRAFT", server_default="DRAFT"
    )
    desired_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotation_weight: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    delivery_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    rotation_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )


class AdvertisingCreative(UtcTimestampMixin, Base):
    __tablename__ = "advertising_creatives"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "version", name="uq_advertising_creatives_campaign_version"
        ),
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'REJECTED', 'CHANGES_REQUESTED')",
            name="valid_review_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(AdvertisingCampaign.id, ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    image_url: Mapped[str | None] = mapped_column(String(2048))
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="PENDING", server_default="PENDING"
    )
    review_note: Mapped[str | None] = mapped_column(String(1000))
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdvertisingReservation(UtcTimestampMixin, Base):
    __tablename__ = "advertising_reservations"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id", "idempotency_key", name="uq_ad_reservations_owner_key"
        ),
        CheckConstraint("start_at < end_at", name="valid_interval"),
        CheckConstraint(
            "status IN ('HELD', 'PAYMENT_PROCESSING', 'CONFIRMED', "
            "'EXPIRED', 'CANCELLED')",
            name="valid_status",
        ),
        Index(
            "ix_ad_reservations_inventory_interval",
            "placement_id",
            "status",
            "start_at",
            "end_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingCampaign.id, ondelete="RESTRICT"), nullable=False
    )
    placement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingPlacement.id, ondelete="RESTRICT"), nullable=False
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="HELD", server_default="HELD"
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)


class AdvertisingBooking(UtcTimestampMixin, Base):
    __tablename__ = "advertising_bookings"
    __table_args__ = (
        UniqueConstraint("reservation_id", name="uq_ad_bookings_reservation"),
        CheckConstraint("start_at < end_at", name="valid_interval"),
        CheckConstraint(
            "status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')",
            name="valid_status",
        ),
        Index(
            "ix_ad_bookings_inventory_interval",
            "placement_id",
            "status",
            "start_at",
            "end_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingCampaign.id, ondelete="RESTRICT"), nullable=False
    )
    placement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingPlacement.id, ondelete="RESTRICT"), nullable=False
    )
    reservation_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(AdvertisingReservation.id, ondelete="RESTRICT"),
        nullable=False,
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="CONFIRMED", server_default="CONFIRMED"
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdvertisingDiscountPolicy(UtcTimestampMixin, Base):
    __tablename__ = "advertising_discount_policies"
    __table_args__ = (
        CheckConstraint("rate_basis_points BETWEEN 0 AND 10000", name="valid_rate"),
        CheckConstraint("annual_allowance_vnd >= 0", name="allowance_nonnegative"),
        CheckConstraint("policy_version > 0", name="version_positive"),
        CheckConstraint(
            "tier IN ('MEMBER', 'SILVER', 'COMPANION', 'PRESTIGE')",
            name="valid_tier",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tier: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    rate_basis_points: Mapped[int] = mapped_column(Integer, nullable=False)
    annual_allowance_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    policy_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class AdvertisingOrder(UtcTimestampMixin, Base):
    __tablename__ = "advertising_orders"
    __table_args__ = (
        UniqueConstraint("reservation_id", name="uq_ad_orders_reservation"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_ad_orders_user_key"),
        CheckConstraint("base_amount_vnd >= 0", name="base_nonnegative"),
        CheckConstraint("discount_amount_vnd >= 0", name="discount_nonnegative"),
        CheckConstraint(
            "payable_amount_vnd = base_amount_vnd - discount_amount_vnd",
            name="amounts_balanced",
        ),
        CheckConstraint("payable_amount_vnd >= 0", name="payable_nonnegative"),
        CheckConstraint(
            "payment_status IN ('PENDING_PAYMENT', 'PAID', 'EXPIRED', "
            "'REFUND_PENDING', 'REFUNDED')",
            name="valid_payment_status",
        ),
        Index("ix_advertising_orders_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reservation_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(AdvertisingReservation.id, ondelete="RESTRICT"),
        nullable=False,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingCampaign.id, ondelete="RESTRICT"), nullable=False
    )
    package_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingPackage.id, ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    price_version: Mapped[int] = mapped_column(Integer, nullable=False)
    membership_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    membership_cycle_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    discount_policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    base_amount_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payable_amount_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="PENDING_PAYMENT",
        server_default="PENDING_PAYMENT",
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payment_idempotency_key: Mapped[str | None] = mapped_column(String(128))
    wallet_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("wallet_journals.id", ondelete="RESTRICT"), unique=True
    )
    allowance_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    pricing_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON_DOCUMENT, nullable=False, default=dict
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdvertisingAuditLog(Base):
    __tablename__ = "advertising_audit_logs"
    __table_args__ = (
        Index("ix_ad_audit_entity_created", "entity_type", "entity_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    before_json: Mapped[dict[str, object] | None] = mapped_column(JSON_DOCUMENT)
    after_json: Mapped[dict[str, object] | None] = mapped_column(JSON_DOCUMENT)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AdvertisingDeliveryStat(Base):
    __tablename__ = "advertising_delivery_stats"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "stat_date", name="uq_ad_delivery_stats_campaign_date"
        ),
        CheckConstraint("delivery_count >= 0", name="delivery_count_nonnegative"),
        CheckConstraint("valid_impressions >= 0", name="impressions_nonnegative"),
        CheckConstraint("valid_clicks >= 0", name="clicks_nonnegative"),
        Index("ix_ad_delivery_stats_placement_date", "placement_id", "stat_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingCampaign.id, ondelete="RESTRICT"), nullable=False
    )
    placement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingPlacement.id, ondelete="RESTRICT"), nullable=False
    )
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    valid_impressions: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    valid_clicks: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )


class AdvertisingDeliveryEvent(Base):
    __tablename__ = "advertising_delivery_events"
    __table_args__ = (
        Index("ix_ad_delivery_events_campaign_selected", "campaign_id", "selected_at"),
        Index("ix_ad_delivery_events_selected", "selected_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingCampaign.id, ondelete="RESTRICT"), nullable=False
    )
    placement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingPlacement.id, ondelete="RESTRICT"), nullable=False
    )
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    impression_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_traffic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class AdvertisingWaitlistEntry(UtcTimestampMixin, Base):
    __tablename__ = "advertising_waitlist_entries"
    __table_args__ = (
        CheckConstraint("start_at < end_at", name="valid_interval"),
        CheckConstraint(
            "status IN ('WAITING', 'NOTIFIED', 'CANCELLED', 'FULFILLED')",
            name="valid_status",
        ),
        UniqueConstraint(
            "owner_user_id",
            "campaign_id",
            "start_at",
            name="uq_ad_waitlist_user_campaign_start",
        ),
        Index(
            "ix_ad_waitlist_placement_status_start",
            "placement_id",
            "status",
            "start_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingCampaign.id, ondelete="RESTRICT"), nullable=False
    )
    placement_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(AdvertisingPlacement.id, ondelete="RESTRICT"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="WAITING", server_default="WAITING"
    )
