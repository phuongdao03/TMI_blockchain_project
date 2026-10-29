from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PromotionAudiencePreview(Base):
    __tablename__ = "promotion_audience_previews"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    policy_version: Mapped[int] = mapped_column(Integer)
    selector_hash: Mapped[str] = mapped_column(String(64))
    candidates_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    eligible_count: Mapped[int] = mapped_column(Integer)
    excluded_count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PromotionDistributionJob(Base):
    __tablename__ = "promotion_distribution_jobs"
    __table_args__ = (
        UniqueConstraint(
            "actor_id", "idempotency_key", name="uq_promotion_distribution_actor_key"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    preview_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("promotion_audience_previews.id", ondelete="RESTRICT")
    )
    idempotency_key: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    candidates_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)
    issued_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_json: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PromotionExpiryReminder(Base):
    __tablename__ = "promotion_expiry_reminders"
    voucher_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("voucher_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    notified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
