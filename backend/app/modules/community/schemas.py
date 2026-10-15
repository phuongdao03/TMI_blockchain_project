import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.community.models import CommunityPostStatus
from app.modules.media.types import COMMUNITY_POST_IMAGE_MAX_COUNT_HARD_LIMIT

_HTML_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def _clean_text(value: str, *, reject_html: bool = False) -> str:
    cleaned = "".join(
        character
        for character in value.replace("\r\n", "\n").replace("\r", "\n")
        if character in "\n\t" or ord(character) >= 32
    ).strip()
    if reject_html and _HTML_TAG.search(cleaned):
        raise ValueError("HTML is not allowed in community posts.")
    return cleaned


class CommunitySchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda name: "".join(
            part.capitalize() if index else part
            for index, part in enumerate(name.split("_"))
        ),
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class CommunityCategoryData(CommunitySchema):
    id: UUID
    name: str
    slug: str
    description: str
    icon: str | None
    sort_order: int


class CommunityAuthorData(CommunitySchema):
    id: UUID
    username: str
    display_name: str
    avatar_url: str | None


class CommunityRelatedWorkData(CommunitySchema):
    id: UUID
    title: str
    slug: str


class CommunityPostImageData(CommunitySchema):
    id: UUID
    url: str


class CommunityTagData(CommunitySchema):
    id: UUID
    name: str
    slug: str


class CommunityPostRequest(CommunitySchema):
    title: Annotated[str, Field(min_length=1, max_length=180)]
    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    category_id: UUID
    related_work_id: UUID | None = None
    image_media_ids: list[UUID] = Field(
        default_factory=list,
        max_length=COMMUNITY_POST_IMAGE_MAX_COUNT_HARD_LIMIT,
    )
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("image_media_ids")
    @classmethod
    def unique_image_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Image media IDs must be unique.")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_unique_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_label in value:
            label = " ".join(raw_label.split())
            if not label or len(label) > 40:
                raise ValueError("Tags must contain 1–40 non-empty characters.")
            folded = label.casefold()
            if folded in seen:
                raise ValueError("Post tags must be unique.")
            seen.add(folded)
            normalized.append(label)
        return normalized

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = _clean_text(value, reject_html=True)
        if not normalized:
            raise ValueError("Title must not be empty.")
        return normalized

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = _clean_text(value, reject_html=True)
        if not normalized:
            raise ValueError("Content must not be empty.")
        return normalized


class CommunityModerationRequest(CommunitySchema):
    reason: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = _clean_text(value)
        if not normalized:
            raise ValueError("A moderation reason is required.")
        return normalized


class CommunityPostData(CommunitySchema):
    id: UUID
    slug: str
    title: str
    excerpt: str
    category: CommunityCategoryData
    author: CommunityAuthorData
    published_at: datetime
    view_count: int
    is_pinned: bool
    like_count: int
    comment_count: int
    viewer_has_liked: bool
    viewer_has_bookmarked: bool
    related_work: CommunityRelatedWorkData | None
    images: list[CommunityPostImageData] = Field(default_factory=list)
    tags: list[CommunityTagData] = Field(default_factory=list)


class CommunityPostDetailData(CommunityPostData):
    content: str


class CommunityPostWriteData(CommunitySchema):
    id: UUID
    slug: str
    title: str
    content: str
    status: CommunityPostStatus
    moderation_reason: str | None
    category: CommunityCategoryData
    related_work: CommunityRelatedWorkData | None
    created_at: datetime
    updated_at: datetime
    view_count: int
    images: list[CommunityPostImageData] = Field(default_factory=list)
    tags: list[CommunityTagData] = Field(default_factory=list)


class CommunityModerationQueueData(CommunityPostWriteData):
    author: CommunityAuthorData
    submitted_at: datetime | None
