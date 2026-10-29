from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoucherReservation(Base):
    __tablename__ = "voucher_reservations"
    __table_args__ = (
        CheckConstraint(
            (
                "discount_vnd > 0 AND original_vnd >= discount_vnd "
                "AND payable_vnd = original_vnd - discount_vnd"
            ),
            name="balanced_amounts",
        ),
        CheckConstraint(
            "status IN ('HELD','REDEEMED','RELEASED')", name="valid_status"
        ),
        Index(
            "uq_voucher_active_order",
            "order_reference",
            unique=True,
            postgresql_where=text("status IN ('HELD','REDEEMED')"),
            sqlite_where=text("status IN ('HELD','REDEEMED')"),
        ),
        Index("ix_voucher_reservations_campaign_status", "campaign_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    voucher_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("voucher_claims.id", ondelete="RESTRICT"), index=True
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("voucher_campaigns.id", ondelete="RESTRICT")
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    order_reference: Mapped[str] = mapped_column(String(180))
    service_code: Mapped[str] = mapped_column(String(40))
    product_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="HELD")
    original_vnd: Mapped[int] = mapped_column(BigInteger)
    discount_vnd: Mapped[int] = mapped_column(BigInteger)
    payable_vnd: Mapped[int] = mapped_column(BigInteger)
    policy_version: Mapped[int] = mapped_column(default=1)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class VoucherAdjustment(Base):
    __tablename__ = "voucher_adjustments"
    __table_args__ = (
        CheckConstraint(
            "discount_vnd >= 0 AND refund_vnd >= 0", name="amounts_nonnegative"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reservation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("voucher_reservations.id", ondelete="RESTRICT"), index=True
    )
    reference: Mapped[str] = mapped_column(String(180), unique=True)
    kind: Mapped[str] = mapped_column(String(24))
    discount_vnd: Mapped[int] = mapped_column(BigInteger, default=0)
    refund_vnd: Mapped[int] = mapped_column(BigInteger, default=0)
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
