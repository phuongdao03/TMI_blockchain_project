from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UtcTimestampMixin
from app.modules.media.models import MediaAsset


class CommunityPostStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    HIDDEN = "HIDDEN"
    DELETED = "DELETED"


class CommunityModerationAction(StrEnum):
    SUBMITTED = "SUBMITTED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    OWNER_DELETED = "OWNER_DELETED"


class CommunityReportReason(StrEnum):
    SPAM = "SPAM"
    HARASSMENT = "HARASSMENT"
    HATE_SPEECH = "HATE_SPEECH"
    MISINFORMATION = "MISINFORMATION"
    COPYRIGHT = "COPYRIGHT"
    ADVERTISING = "ADVERTISING"
    PRIVACY_VIOLATION = "PRIVACY_VIOLATION"
    OTHER = "OTHER"


class CommunityReportStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class CommunityReportResolution(StrEnum):
    HIDE = "HIDE"
    DISMISS = "DISMISS"


class CommunityModerationEventAction(StrEnum):
    SUBMITTED = "SUBMITTED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    OWNER_DELETED = "OWNER_DELETED"
    POST_HIDDEN = "POST_HIDDEN"
    POST_RESTORED = "POST_RESTORED"
    COMMENT_HIDDEN = "COMMENT_HIDDEN"
    COMMENT_RESTORED = "COMMENT_RESTORED"
    REPORT_DISMISSED = "REPORT_DISMISSED"
    CATEGORY_CREATED = "CATEGORY_CREATED"
    CATEGORY_UPDATED = "CATEGORY_UPDATED"
    SETTINGS_UPDATED = "SETTINGS_UPDATED"
    POST_PINNED = "POST_PINNED"
    POST_UNPINNED = "POST_UNPINNED"
    COMMENTS_LOCKED = "COMMENTS_LOCKED"
    COMMENTS_UNLOCKED = "COMMENTS_UNLOCKED"
    POST_ADMIN_DELETED = "POST_ADMIN_DELETED"
    POST_ADMIN_RESTORED = "POST_ADMIN_RESTORED"
    COMMENT_ADMIN_DELETED = "COMMENT_ADMIN_DELETED"
    COMMENT_ADMIN_RESTORED = "COMMENT_ADMIN_RESTORED"
    MEMBER_RESTRICTED = "MEMBER_RESTRICTED"
    MEMBER_RESTRICTION_REVOKED = "MEMBER_RESTRICTION_REVOKED"


class CommunityProfile(UtcTimestampMixin, Base):
    __tablename__ = "community_profiles"
    __table_args__ = (
        CheckConstraint("length(trim(username)) > 0", name="username_not_empty"),
        Index("ix_community_profiles_display_name", "display_name"),
        Index(
            "uq_community_profiles_avatar_media_id",
            "avatar_media_id",
            unique=True,
        ),
        Index(
            "uq_community_profiles_username_ci",
            text("lower(username)"),
            unique=True,
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    avatar_media_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="SET NULL"),
    )
    bio: Mapped[str | None] = mapped_column(String(500))


class CommunityCategory(UtcTimestampMixin, Base):
    __tablename__ = "community_categories"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        Index("ix_community_categories_active_order", "is_active", "sort_order"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=text("true")
    )


class CommunityTag(UtcTimestampMixin, Base):
    __tablename__ = "community_tags"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        CheckConstraint("length(trim(slug)) > 0", name="slug_not_empty"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    post_relations: Mapped[list["CommunityPostTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
    )


class CommunityPost(UtcTimestampMixin, Base):
    __tablename__ = "community_posts"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="title_not_empty"),
        CheckConstraint("length(trim(content)) > 0", name="content_not_empty"),
        CheckConstraint("length(trim(slug)) > 0", name="slug_not_empty"),
        CheckConstraint("view_count >= 0", name="view_count_non_negative"),
        Index(
            "ix_community_posts_status_published",
            "status",
            "published_at",
            "id",
        ),
        Index(
            "ix_community_posts_category_status_published",
            "category_id",
            "status",
            "published_at",
        ),
        Index("ix_community_posts_author_updated", "author_user_id", "updated_at"),
        Index("ix_community_posts_related_work_id", "related_work_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    author_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    related_work_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("public_works.id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[CommunityPostStatus] = mapped_column(
        Enum(
            CommunityPostStatus,
            name="community_post_status",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=CommunityPostStatus.DRAFT,
        server_default=CommunityPostStatus.DRAFT.value,
    )
    moderation_reason: Mapped[str | None] = mapped_column(Text)
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comments_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pre_delete_status: Mapped[str | None] = mapped_column(String(16))
    admin_deleted: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    image_relations: Mapped[list["CommunityPostMedia"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="CommunityPostMedia.sort_order",
    )
    tag_relations: Mapped[list["CommunityPostTag"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="CommunityPostTag.tag_id",
    )


class CommunityPostTag(Base):
    __tablename__ = "community_post_tags"
    __table_args__ = (Index("ix_community_post_tags_tag_post", "tag_id", "post_id"),)

    post_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_tags.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    post: Mapped[CommunityPost] = relationship(back_populates="tag_relations")
    tag: Mapped[CommunityTag] = relationship(back_populates="post_relations")


class CommunityPostMedia(Base):
    __tablename__ = "community_post_media"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        UniqueConstraint("media_asset_id", name="uq_community_post_media_asset"),
        UniqueConstraint(
            "post_id",
            "sort_order",
            name="uq_community_post_media_order",
        ),
        Index("ix_community_post_media_post_order", "post_id", "sort_order"),
    )

    post_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    media_asset_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    post: Mapped[CommunityPost] = relationship(back_populates="image_relations")
    media_asset: Mapped[MediaAsset] = relationship()


class CommunityModerationLog(Base):
    __tablename__ = "community_moderation_logs"
    __table_args__ = (
        CheckConstraint(
            "action IN ('SUBMITTED', 'PUBLISHED', 'REJECTED', 'OWNER_DELETED')",
            name="action_valid",
        ),
        Index("ix_community_moderation_logs_post_created", "post_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_posts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[CommunityModerationAction] = mapped_column(
        Enum(
            CommunityModerationAction,
            name="community_moderation_action",
            values_callable=lambda values: [value.value for value in values],
            validate_strings=True,
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class CommunityComment(Base):
    __tablename__ = "community_comments"
    __table_args__ = (
        CheckConstraint("length(trim(content)) > 0", name="content_not_empty"),
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="parent_not_self",
        ),
        Index(
            "ix_community_comments_post_parent_created",
            "post_id",
            "parent_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_posts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    author_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("community_comments.id", ondelete="RESTRICT"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moderation_hidden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    admin_deleted: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    pre_delete_hidden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class CommunityMemberRestriction(UtcTimestampMixin, Base):
    __tablename__ = "community_member_restrictions"
    __table_args__ = (
        CheckConstraint("scope IN ('POSTS', 'COMMENTS')", name="scope_valid"),
        CheckConstraint("expires_at > starts_at", name="time_range_valid"),
        CheckConstraint("length(trim(reason)) > 0", name="reason_not_empty"),
        Index(
            "ix_community_member_restrictions_member_scope",
            "member_user_id",
            "scope",
        ),
        Index("ix_community_member_restrictions_expires", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    member_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    revocation_reason: Mapped[str | None] = mapped_column(Text)
    revoked_request_id: Mapped[str | None] = mapped_column(String(128))


class CommunityReport(Base):
    __tablename__ = "community_reports"
    __table_args__ = (
        CheckConstraint(
            "(post_id IS NOT NULL AND comment_id IS NULL) OR "
            "(post_id IS NULL AND comment_id IS NOT NULL)",
            name="one_target",
        ),
        CheckConstraint(
            "reason IN ('SPAM', 'HARASSMENT', 'HATE_SPEECH', 'MISINFORMATION', "
            "'COPYRIGHT', 'ADVERTISING', 'PRIVACY_VIOLATION', 'OTHER')",
            name="reason_valid",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'DISMISSED')",
            name="status_valid",
        ),
        CheckConstraint(
            "resolution_action IS NULL OR resolution_action IN ('HIDE', 'DISMISS')",
            name="resolution_valid",
        ),
        CheckConstraint(
            "length(details) <= 2000 OR details IS NULL",
            name="details_length",
        ),
        CheckConstraint(
            "(status = 'OPEN' AND resolved_at IS NULL AND "
            "resolved_by_user_id IS NULL AND resolution_action IS NULL AND "
            "resolution_reason IS NULL) OR "
            "(status IN ('RESOLVED', 'DISMISSED') AND resolved_at IS NOT NULL AND "
            "resolved_by_user_id IS NOT NULL AND resolution_action IS NOT NULL AND "
            "resolution_reason IS NOT NULL)",
            name="resolution_state_consistent",
        ),
        Index("ix_community_reports_status_created", "status", "created_at"),
        Index(
            "uq_community_reports_open_reporter_post",
            "reporter_user_id",
            "post_id",
            unique=True,
            postgresql_where=text("status = 'OPEN' AND post_id IS NOT NULL"),
            sqlite_where=text("status = 'OPEN' AND post_id IS NOT NULL"),
        ),
        Index(
            "uq_community_reports_open_reporter_comment",
            "reporter_user_id",
            "comment_id",
            unique=True,
            postgresql_where=text("status = 'OPEN' AND comment_id IS NOT NULL"),
            sqlite_where=text("status = 'OPEN' AND comment_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reporter_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    post_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("community_posts.id", ondelete="RESTRICT"),
    )
    comment_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("community_comments.id", ondelete="RESTRICT"),
    )
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="OPEN", server_default="OPEN"
    )
    resolution_action: Mapped[str | None] = mapped_column(String(16))
    resolution_reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    resolved_request_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )


class CommunitySettings(Base):
    __tablename__ = "community_settings"
    __table_args__ = (CheckConstraint("singleton_id = 1", name="singleton_id_valid"),)

    singleton_id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    pre_moderation_enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class CommunityModerationEvent(Base):
    __tablename__ = "community_moderation_events"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('POST', 'COMMENT', 'CATEGORY', 'SETTINGS', 'MEMBER')",
            name="target_type_valid",
        ),
        CheckConstraint("length(trim(target_id)) > 0", name="target_id_not_empty"),
        CheckConstraint(
            "action IN ('SUBMITTED', 'PUBLISHED', 'REJECTED', 'OWNER_DELETED', "
            "'POST_HIDDEN', 'POST_RESTORED', 'COMMENT_HIDDEN', "
            "'COMMENT_RESTORED', 'REPORT_DISMISSED', 'CATEGORY_CREATED', "
            "'CATEGORY_UPDATED', 'SETTINGS_UPDATED', 'POST_PINNED', "
            "'POST_UNPINNED', 'COMMENTS_LOCKED', 'COMMENTS_UNLOCKED', "
            "'POST_ADMIN_DELETED', 'POST_ADMIN_RESTORED', "
            "'COMMENT_ADMIN_DELETED', 'COMMENT_ADMIN_RESTORED', "
            "'MEMBER_RESTRICTED', 'MEMBER_RESTRICTION_REVOKED')",
            name="action_valid",
        ),
        Index(
            "ix_community_moderation_events_target_created",
            "target_type",
            "target_id",
            "created_at",
        ),
        Index("ix_community_moderation_events_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    report_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("community_reports.id", ondelete="RESTRICT"),
    )
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_data: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class CommunityLike(UtcTimestampMixin, Base):
    __tablename__ = "community_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="post_user"),
        Index("ix_community_likes_post", "post_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )


class CommunityBookmark(UtcTimestampMixin, Base):
    __tablename__ = "community_bookmarks"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="post_user"),
        Index("ix_community_bookmarks_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )


class CommunityFollow(UtcTimestampMixin, Base):
    __tablename__ = "community_follows"
    __table_args__ = (
        UniqueConstraint("follower_user_id", "followed_user_id", name="pair"),
        CheckConstraint(
            "follower_user_id <> followed_user_id",
            name="self_follow_not_allowed",
        ),
        Index("ix_community_follows_followed", "followed_user_id"),
        Index("ix_community_follows_follower", "follower_user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    follower_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    followed_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )


class CommunityCommentLike(UtcTimestampMixin, Base):
    __tablename__ = "community_comment_likes"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="comment_user"),
        Index("ix_community_comment_likes_comment", "comment_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    comment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("community_comments.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
