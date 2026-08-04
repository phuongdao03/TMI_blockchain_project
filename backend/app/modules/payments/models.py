from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    REFUNDED = "REFUNDED"


PAYMENT_JSON = JSONB().with_variant(JSON(), "sqlite")


class PaymentOrder(UtcTimestampMixin, Base):
    __tablename__ = "payment_orders"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
        Index("ix_payment_orders_dossier_status", "dossier_id", "status"),
        Index(
            "ix_payment_orders_provider_provider_order_id",
            "provider",
            "provider_order_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    order_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
    )
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_order_id: Mapped[str | None] = mapped_column(String(128))
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name="payment_status",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        PAYMENT_JSON,
        nullable=False,
        default=dict,
    )


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    payment_order_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("payment_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_event_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload_redacted: Mapped[dict[str, object]] = mapped_column(
        PAYMENT_JSON,
        nullable=False,
        default=dict,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
