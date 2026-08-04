from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class MediaStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    QUARANTINED = "QUARANTINED"
    DELETED = "DELETED"


class MediaAsset(UtcTimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("bytes >= 0", name="bytes_non_negative"),
        CheckConstraint(
            "cloudinary_version IS NULL OR cloudinary_version >= 0",
            name="cloudinary_version_non_negative",
        ),
        CheckConstraint(
            "width IS NULL OR width >= 0",
            name="width_non_negative",
        ),
        CheckConstraint(
            "height IS NULL OR height >= 0",
            name="height_non_negative",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="duration_ms_non_negative",
        ),
        Index(
            "ix_media_assets_owner_status_created_at",
            "owner_user_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_media_assets_status_created_at",
            "status",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cloudinary_public_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )
    cloudinary_version: Mapped[int | None] = mapped_column(BigInteger)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    access_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(CHAR(64))
    status: Mapped[MediaStatus] = mapped_column(
        Enum(
            MediaStatus,
            name="media_status",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=MediaStatus.PENDING,
        server_default=MediaStatus.PENDING.value,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
