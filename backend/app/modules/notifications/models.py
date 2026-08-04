from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationChannel(StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class DeliveryStatus(StrEnum):
    PENDING = "PENDING"
    RETRY_PENDING = "RETRY_PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


CHANNEL_TYPE = Enum(
    NotificationChannel,
    name="notification_channel",
    values_callable=lambda x: [v.value for v in x],
    native_enum=False,
    create_constraint=True,
)
DELIVERY_STATUS_TYPE = Enum(
    DeliveryStatus,
    name="notification_delivery_status",
    values_callable=lambda x: [v.value for v in x],
    native_enum=False,
    create_constraint=True,
)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "source_event_id", name="uq_notifications_user_source_event"
        ),
        Index("ix_notifications_user_read_created", "user_id", "read_at", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_event_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "notification_id", "channel", name="uq_notification_deliveries_channel"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    notification_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(CHANNEL_TYPE, nullable=False)
    destination_masked: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[DeliveryStatus] = mapped_column(
        DELIVERY_STATUS_TYPE, nullable=False, server_default="PENDING"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
