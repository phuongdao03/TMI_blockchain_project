from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class CmsContentStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


CMS_STATUS_TYPE = Enum(
    CmsContentStatus,
    name="cms_content_status",
    values_callable=lambda values: [value.value for value in values],
    native_enum=False,
    create_constraint=True,
)


class CmsCategory(UtcTimestampMixin, Base):
    __tablename__ = "cms_categories"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class CmsPost(UtcTimestampMixin, Base):
    __tablename__ = "cms_posts"
    __table_args__ = (Index("ix_cms_posts_status_published", "status", "published_at"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("cms_categories.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    excerpt: Mapped[str | None] = mapped_column(String(500))
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CmsContentStatus] = mapped_column(
        CMS_STATUS_TYPE,
        nullable=False,
        default=CmsContentStatus.DRAFT,
        server_default="DRAFT",
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    updated_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )


class CmsPage(UtcTimestampMixin, Base):
    __tablename__ = "cms_pages"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CmsContentStatus] = mapped_column(
        CMS_STATUS_TYPE, nullable=False, server_default="DRAFT"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    updated_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )


class CmsBanner(UtcTimestampMixin, Base):
    __tablename__ = "cms_banners"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    image_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    link_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[CmsContentStatus] = mapped_column(
        CMS_STATUS_TYPE, nullable=False, server_default="DRAFT"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    updated_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )


GUIDE_AUDIENCES = frozenset(
    {"PUBLIC", "VIEWER", "USER", "MODERATOR", "SUPER_ADMIN", "EMPLOYEE"}
)


class CmsGuideArticle(UtcTimestampMixin, Base):
    __tablename__ = "cms_guide_articles"
    __table_args__ = (
        Index("ix_cms_guide_articles_status_order", "status", "sort_order", "slug"),
        Index("ix_cms_guide_articles_search_text", "search_text"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    audiences: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: ["PUBLIC"],
        server_default='["PUBLIC"]',
    )
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    search_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    search_title: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    search_summary: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    status: Mapped[CmsContentStatus] = mapped_column(
        CMS_STATUS_TYPE,
        nullable=False,
        default=CmsContentStatus.DRAFT,
        server_default="DRAFT",
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )


class CmsGuideFeedback(Base):
    __tablename__ = "cms_guide_feedback"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "client_token_hash",
            name="uq_cms_guide_feedback_article_client",
        ),
        Index("ix_cms_guide_feedback_article_created", "article_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("cms_guide_articles.id", ondelete="CASCADE"), nullable=False
    )
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(500))
    client_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CmsVersion(Base):
    __tablename__ = "cms_versions"
    __table_args__ = (
        Index("ix_cms_versions_resource", "resource_type", "resource_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
