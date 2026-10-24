from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class Wallet(UtcTimestampMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("balance_minor >= 0", name="nonnegative_balance"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    balance_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )


class WalletTopup(UtcTimestampMixin, Base):
    __tablename__ = "wallet_topups"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_wallet_topups_user_key"
        ),
        CheckConstraint(
            "amount_minor >= 1000 AND amount_minor <= 1000000000", name="amount_range"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'PAID', "
            "'FAILED', 'CANCELLED', 'EXPIRED')",
            name="valid_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    order_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_order_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PROCESSING"
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checkout_url: Mapped[str | None] = mapped_column(String(2048))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WalletJournal(Base):
    """Immutable balanced two-leg posting; amounts always represent integer VND."""

    __tablename__ = "wallet_journals"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_wallet_journals_user_key"
        ),
        CheckConstraint(
            "wallet_delta != 0 AND wallet_delta + counter_delta = 0",
            name="balanced_legs",
        ),
        CheckConstraint("balance_after >= 0", name="nonnegative_balance"),
        CheckConstraint("kind IN ('TOPUP', 'PAYMENT', 'REVERSAL')", name="valid_kind"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("wallets.user_id", ondelete="RESTRICT"), index=True
    )
    wallet_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    counter_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_reference: Mapped[str] = mapped_column(
        String(160), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WalletTopupEvent(Base):
    __tablename__ = "wallet_topup_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_wallet_topup_events_provider_event",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    topup_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("wallet_topups.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_redacted: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
