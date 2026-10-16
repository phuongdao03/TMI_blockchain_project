import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.modules.community.models import CommunityReportReason
from app.modules.community.schemas import (
    CommunityAuthorData,
    CommunityCategoryData,
    CommunityPostImageData,
    CommunityRelatedWorkData,
    CommunitySchema,
    CommunityTagData,
)

_HTML_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_CATEGORY_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _plain_text(value: str, *, max_length: int) -> str:
    cleaned = "".join(
        character
        for character in value.replace("\r\n", "\n").replace("\r", "\n")
        if character in "\n\t" or ord(character) >= 32
    ).strip()
    if not cleaned or len(cleaned) > max_length or _HTML_TAG.search(cleaned):
        raise ValueError("Value must be non-empty plain text within the size limit.")
    return cleaned


class CommunityReportRequest(CommunitySchema):
    reason: CommunityReportReason
    details: Annotated[str | None, Field(max_length=2_000)] = None

    @field_validator("details")
    @classmethod
    def normalize_details(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _plain_text(value, max_length=2_000)


class CommunityReportResolutionRequest(CommunitySchema):
    action: Literal["HIDE", "DISMISS"]
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return _plain_text(value, max_length=2_000)


class CommunityCategoryCreateRequest(CommunitySchema):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    slug: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(min_length=1, max_length=2_000)]
    icon: Annotated[str | None, Field(max_length=64)] = None
    sort_order: Annotated[int, Field(ge=0)] = 0
    is_active: bool = True
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _plain_text(value, max_length=120)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        if not _CATEGORY_SLUG.fullmatch(value):
            raise ValueError(
                "Category slug must use lowercase letters, digits, and hyphens."
            )
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return _plain_text(value, max_length=2_000)

    @field_validator("icon")
    @classmethod
    def normalize_icon(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _plain_text(value, max_length=64)

    @field_validator("reason")
    @classmethod
    def normalize_audit_reason(cls, value: str) -> str:
        return _plain_text(value, max_length=2_000)


class CommunityCategoryPatchRequest(CommunitySchema):
    name: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    slug: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    description: Annotated[str | None, Field(min_length=1, max_length=2_000)] = None
    icon: Annotated[str | None, Field(max_length=64)] = None
    sort_order: Annotated[int | None, Field(ge=0)] = None
    is_active: bool | None = None
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]

    @model_validator(mode="after")
    def validate_patch(self) -> "CommunityCategoryPatchRequest":
        fields = self.model_fields_set - {"reason"}
        if not fields:
            raise ValueError("At least one category field must be provided.")
        if any(getattr(self, field) is None for field in fields - {"icon"}):
            raise ValueError("Only icon may be explicitly cleared.")
        if self.slug is not None and not _CATEGORY_SLUG.fullmatch(self.slug):
            raise ValueError(
                "Category slug must use lowercase letters, digits, and hyphens."
            )
        if self.name is not None:
            self.name = _plain_text(self.name, max_length=120)
        if self.description is not None:
            self.description = _plain_text(self.description, max_length=2_000)
        if self.icon is not None:
            self.icon = _plain_text(self.icon, max_length=64)
        self.reason = _plain_text(self.reason, max_length=2_000)
        return self


class CommunityActionRequest(CommunitySchema):
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return _plain_text(value, max_length=2_000)


class CommunityReportPostPreview(CommunitySchema):
    type: Literal["POST"]
    id: UUID
    slug: str
    title: str
    excerpt: str
    author: CommunityAuthorData


class CommunityReportCommentPreview(CommunitySchema):
    type: Literal["COMMENT"]
    id: UUID
    post_id: UUID
    post_slug: str
    post_title: str
    content: str
    is_deleted: bool
    author: CommunityAuthorData | None


class CommunityReportData(CommunitySchema):
    id: UUID
    target_type: Literal["POST", "COMMENT"]
    target_id: UUID
    status: Literal["OPEN", "RESOLVED", "DISMISSED"]
    reason: CommunityReportReason
    details: str | None
    created_at: datetime
    resolved_at: datetime | None
    resolution_action: Literal["HIDE", "DISMISS"] | None
    resolution_reason: str | None
    reporter: CommunityAuthorData
    target_preview: CommunityReportPostPreview | CommunityReportCommentPreview


class CommunityAdminCategoryData(CommunitySchema):
    id: UUID
    name: str
    slug: str
    description: str
    icon: str | None
    sort_order: int
    is_active: bool


class CommunityModerationStateData(CommunitySchema):
    target_type: Literal["POST", "COMMENT"]
    target_id: UUID
    state: Literal["HIDDEN", "VISIBLE"]


class CommunityModerationEventData(CommunitySchema):
    id: UUID
    target_type: Literal["POST", "COMMENT", "MEMBER", "CATEGORY", "SETTINGS"]
    target_id: str
    action: str
    actor_id: UUID
    actor: CommunityAuthorData
    reason: str | None
    request_id: str
    created_at: datetime
    event_data: dict[str, object] | None = Field(alias="metadata")


class CommunityAdminPostWorkspaceData(CommunitySchema):
    id: UUID
    slug: str
    title: str
    excerpt: str
    content: str
    category: CommunityCategoryData
    author: CommunityAuthorData
    published_at: datetime | None
    status: Literal["DRAFT", "PENDING", "PUBLISHED", "REJECTED", "HIDDEN", "DELETED"]
    view_count: int
    is_pinned: bool
    like_count: int
    comment_count: int
    viewer_has_liked: bool
    viewer_has_bookmarked: bool
    related_work: CommunityRelatedWorkData | None
    images: list[CommunityPostImageData] = Field(default_factory=list)
    tags: list[CommunityTagData] = Field(default_factory=list)
    comments_locked: bool
    deleted_at: datetime | None
    pre_delete_status: str | None


class CommunityAdminPostPinData(CommunitySchema):
    post_id: UUID
    is_pinned: bool


class CommunityAdminPostLockData(CommunitySchema):
    post_id: UUID
    comments_locked: bool


class CommunityAdminPostDeletionData(CommunitySchema):
    post_id: UUID
    is_deleted: bool
    deleted_at: datetime | None
    restored_status: str | None


class CommunityAdminCommentPostData(CommunitySchema):
    id: UUID
    slug: str
    title: str


class CommunityAdminCommentWorkspaceData(CommunitySchema):
    id: UUID
    post_id: UUID
    parent_id: UUID | None
    content: str
    author: CommunityAuthorData | None
    is_deleted: bool
    created_at: datetime
    like_count: int
    viewer_has_liked: bool
    visibility: Literal["VISIBLE", "HIDDEN", "DELETED"]
    post: CommunityAdminCommentPostData


class CommunityAdminCommentStateData(CommunitySchema):
    comment_id: UUID
    visibility: Literal["VISIBLE", "HIDDEN", "DELETED"]


class CommunityAdminMemberCard(CommunitySchema):
    id: UUID
    username: str
    display_name: str
    avatar_url: str | None


class CommunityAdminActiveRestriction(CommunitySchema):
    id: UUID
    scope: Literal["POSTS", "COMMENTS"]
    expires_at: datetime


class CommunityAdminMemberWorkspaceData(CommunitySchema):
    member: CommunityAdminMemberCard
    published_post_count: int
    comment_count: int
    follower_count: int
    following_count: int
    last_activity_at: datetime | None
    active_restrictions: list[CommunityAdminActiveRestriction]


class CommunityMemberRestrictionCreateRequest(CommunitySchema):
    scope: Literal["POSTS", "COMMENTS"]
    duration_minutes: Annotated[int, Field(ge=1, le=525_600)]
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return _plain_text(value, max_length=2_000)


class CommunityMemberRestrictionData(CommunitySchema):
    id: UUID
    member: CommunityAdminMemberCard
    scope: Literal["POSTS", "COMMENTS"]
    status: Literal["ACTIVE", "EXPIRED", "REVOKED"]
    reason: str
    starts_at: datetime
    expires_at: datetime
    actor: CommunityAuthorData
    request_id: str


class CommunityMemberRestrictionRevokeRequest(CommunitySchema):
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return _plain_text(value, max_length=2_000)
