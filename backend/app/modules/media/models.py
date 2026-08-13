import builtins
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
    LargeBinary,
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
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class MediaConfidentiality(StrEnum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"


class MediaEncryptionStatus(StrEnum):
    PENDING = "PENDING"
    ENCRYPTED = "ENCRYPTED"
    NOT_REQUIRED = "NOT_REQUIRED"
    LEGACY_UNENCRYPTED = "LEGACY_UNENCRYPTED"
    FAILED = "FAILED"


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
        CheckConstraint(
            "inspection_attempts >= 0",
            name="inspection_attempts_non_negative",
        ),
        CheckConstraint(
            "hash_byte_length IS NULL OR hash_byte_length >= 0",
            name="hash_byte_length_non_negative",
        ),
        CheckConstraint(
            "hash_storage_version IS NULL OR hash_storage_version >= 0",
            name="hash_storage_version_non_negative",
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
    perceptual_hash: Mapped[str | None] = mapped_column(CHAR(16))
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
    inspection_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    inspection_reason_code: Mapped[str | None] = mapped_column(String(64))
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hash_algorithm: Mapped[str | None] = mapped_column(String(16))
    hash_byte_length: Mapped[int | None] = mapped_column(BigInteger)
    inspection_policy_version: Mapped[str | None] = mapped_column(String(64))
    hash_storage_version: Mapped[int | None] = mapped_column(BigInteger)
    hash_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidentiality: Mapped[MediaConfidentiality] = mapped_column(
        Enum(
            MediaConfidentiality,
            name="media_confidentiality",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=MediaConfidentiality.PRIVATE,
        server_default=MediaConfidentiality.PRIVATE.value,
    )
    encryption_status: Mapped[MediaEncryptionStatus] = mapped_column(
        Enum(
            MediaEncryptionStatus,
            name="media_encryption_status",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=MediaEncryptionStatus.PENDING,
        server_default=MediaEncryptionStatus.PENDING.value,
    )
    encryption_algorithm: Mapped[str | None] = mapped_column(String(32))
    encryption_key_id: Mapped[str | None] = mapped_column(String(64))
    encryption_nonce: Mapped[builtins.bytes | None] = mapped_column(
        LargeBinary(12),
        nullable=True,
    )
    encryption_tag: Mapped[builtins.bytes | None] = mapped_column(
        LargeBinary(16),
        nullable=True,
    )
    encrypted_object_public_id: Mapped[str | None] = mapped_column(Text, unique=True)
    encrypted_object_version: Mapped[int | None] = mapped_column(BigInteger)
    encrypted_bytes: Mapped[int | None] = mapped_column(BigInteger)
    encrypted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
