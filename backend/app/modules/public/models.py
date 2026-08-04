from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class PublicationStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_PUBLICATION = "PENDING_PUBLICATION"
    PUBLISHED = "PUBLISHED"
    HIDDEN = "HIDDEN"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class PublicWorkVisibility(StrEnum):
    PRIVATE = "PRIVATE"
    UNLISTED = "UNLISTED"
    PUBLIC = "PUBLIC"


class PublicMediaKind(StrEnum):
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"


class DerivativeStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class ContentReportReason(StrEnum):
    COPYRIGHT = "COPYRIGHT"
    INCORRECT_INFORMATION = "INCORRECT_INFORMATION"
    INAPPROPRIATE_CONTENT = "INAPPROPRIATE_CONTENT"
    OTHER = "OTHER"


class ContentReportStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"
    SUSPENDED = "SUSPENDED"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda values: [value.value for value in values],
        validate_strings=True,
        native_enum=False,
        create_constraint=True,
    )


class PublicWork(UtcTimestampMixin, Base):
    __tablename__ = "public_works"
    __table_args__ = (
        UniqueConstraint(
            "dossier_id",
            name="uq_public_works_dossier_id",
        ),
        CheckConstraint("view_count >= 0", name="view_count_non_negative"),
        CheckConstraint("version > 0", name="version_positive"),
        Index(
            "ix_public_works_status_visibility_published",
            "publication_status",
            "visibility",
            "published_at",
        ),
        Index(
            "ix_public_works_category_status_visibility",
            "category_id",
            "publication_status",
            "visibility",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dossier_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("dossiers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    certificate_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("certificates.id", ondelete="RESTRICT"),
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
    )
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)
    full_description: Mapped[str | None] = mapped_column(Text)
    publication_status: Mapped[PublicationStatus] = mapped_column(
        _enum(PublicationStatus, "publication_status"),
        nullable=False,
        default=PublicationStatus.DRAFT,
        server_default=PublicationStatus.DRAFT.value,
    )
    visibility: Mapped[PublicWorkVisibility] = mapped_column(
        _enum(PublicWorkVisibility, "public_work_visibility"),
        nullable=False,
        default=PublicWorkVisibility.PRIVATE,
        server_default=PublicWorkVisibility.PRIVATE.value,
    )
    author_display_name: Mapped[str | None] = mapped_column(String(255))
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    thumbnail_media_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    featured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    featured_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    view_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_organization_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    search_taxonomy_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    search_certificate_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"),
        nullable=False,
        default="",
        server_default="",
    )


class PublicWorkSlugHistory(Base):
    __tablename__ = "public_work_slug_history"
    __table_args__ = (
        Index(
            "ix_public_work_slug_history_work_created",
            "public_work_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="CASCADE"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PublicTag(UtcTimestampMixin, Base):
    __tablename__ = "public_tags"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )


class PublicWorkTag(Base):
    __tablename__ = "public_work_tags"

    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_tags.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PublicWorkMedia(UtcTimestampMixin, Base):
    __tablename__ = "public_work_media"
    __table_args__ = (
        UniqueConstraint(
            "public_work_id",
            "media_asset_id",
            name="uq_public_work_media_work_asset",
        ),
        CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        Index(
            "ix_public_work_media_work_order",
            "public_work_id",
            "sort_order",
            "created_at",
        ),
        Index(
            "ix_public_work_media_derivative_status",
            "derivative_status",
            "updated_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    media_kind: Mapped[PublicMediaKind] = mapped_column(
        _enum(PublicMediaKind, "public_media_kind"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    caption: Mapped[str | None] = mapped_column(String(500))
    alt_text: Mapped[str | None] = mapped_column(String(500))
    derivative_status: Mapped[DerivativeStatus] = mapped_column(
        _enum(DerivativeStatus, "public_media_derivative_status"),
        nullable=False,
        default=DerivativeStatus.PENDING,
        server_default=DerivativeStatus.PENDING.value,
    )
    derivative_url: Mapped[str | None] = mapped_column(Text)
    derivative_public_id: Mapped[str | None] = mapped_column(Text)
    derivative_mime_type: Mapped[str | None] = mapped_column(String(127))
    derivative_width: Mapped[int | None] = mapped_column(Integer)
    derivative_height: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    failure_code: Mapped[str | None] = mapped_column(String(64))


class ContentReport(UtcTimestampMixin, Base):
    __tablename__ = "content_reports"
    __table_args__ = (
        Index("ix_content_reports_status_created", "status", "created_at"),
        Index("ix_content_reports_work_created", "public_work_id", "created_at"),
        UniqueConstraint("dedup_key", name="uq_content_reports_dedup_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    public_work_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reporter_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    reporter_email_hash: Mapped[str | None] = mapped_column(String(64))
    reporter_email_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    reason: Mapped[ContentReportReason] = mapped_column(
        _enum(ContentReportReason, "content_report_reason"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)
    reporter_ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ContentReportStatus] = mapped_column(
        _enum(ContentReportStatus, "content_report_status"),
        nullable=False,
        default=ContentReportStatus.OPEN,
        server_default=ContentReportStatus.OPEN.value,
    )
    assigned_to_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
