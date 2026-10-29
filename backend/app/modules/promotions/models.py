from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoucherCampaign(Base):
    __tablename__ = "voucher_campaigns"
    __table_args__ = (
        CheckConstraint("amount_vnd > 0", name="amount_positive"),
        CheckConstraint("validity_days > 0", name="validity_positive"),
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="valid_period",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    public_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    terms: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str] = mapped_column(String(512))
    amount_vnd: Mapped[int] = mapped_column(Integer)
    validity_days: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    name: Mapped[str] = mapped_column(String(255), default="")
    internal_description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    program_type: Mapped[str] = mapped_column(String(16), default="CLAIM")
    policy_version: Mapped[int] = mapped_column(Integer, default=1)
    policy_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    budget_reserved_vnd: Mapped[int] = mapped_column(BigInteger, default=0)
    budget_spent_vnd: Mapped[int] = mapped_column(BigInteger, default=0)
    created_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VoucherClaim(Base):
    __tablename__ = "voucher_claims"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "campaign_id",
            "issuance_slot",
            name="uq_voucher_claims_user_campaign_slot",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("voucher_campaigns.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(255))
    terms: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str] = mapped_column(String(512))
    amount_vnd: Mapped[int] = mapped_column(Integer)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    policy_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    policy_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="AVAILABLE", index=True)
    unique_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uses_used: Mapped[int] = mapped_column(Integer, default=0)
    issue_reason: Mapped[str] = mapped_column(String(255), default="claim")
    issuance_slot: Mapped[int] = mapped_column(Integer, default=1)


class VoucherPresentationState(Base):
    __tablename__ = "voucher_presentation_states"
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("voucher_campaigns.id", ondelete="RESTRICT"), primary_key=True
    )
    seen_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opt_out: Mapped[bool] = mapped_column(Boolean, default=False)
    last_session_id: Mapped[UUID | None] = mapped_column(Uuid)
