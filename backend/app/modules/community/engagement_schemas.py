import re
from datetime import datetime
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.modules.community.schemas import CommunityAuthorData, CommunitySchema

_HTML_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


class CommunityCommentRequest(CommunitySchema):
    content: Annotated[str, Field(min_length=1, max_length=10_000)]
    parent_id: UUID | None = None

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        content = "".join(
            character
            for character in value.replace("\r\n", "\n").replace("\r", "\n")
            if character in "\n\t" or ord(character) >= 32
        ).strip()
        if not content:
            raise ValueError("Comment content must not be empty.")
        if _HTML_TAG.search(content):
            raise ValueError("HTML is not allowed in community comments.")
        return content


class CommunityCommentEditRequest(CommunitySchema):
    content: Annotated[str, Field(min_length=1, max_length=10_000)]

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        content = "".join(
            character
            for character in value.replace("\r\n", "\n").replace("\r", "\n")
            if character in "\n\t" or ord(character) >= 32
        ).strip()
        if not content:
            raise ValueError("Comment content must not be empty.")
        if _HTML_TAG.search(content):
            raise ValueError("HTML is not allowed in community comments.")
        return content


class CommunityCommentData(CommunitySchema):
    id: UUID
    post_id: UUID
    parent_id: UUID | None
    content: str
    author: CommunityAuthorData | None
    is_deleted: bool
    created_at: datetime
    like_count: int = 0
    viewer_has_liked: bool = False


class CommunityCommentReplyData(CommunitySchema):
    id: UUID
    parent_id: UUID
    content: str
    author: CommunityAuthorData | None
    is_deleted: bool
    created_at: datetime
    like_count: int = 0
    viewer_has_liked: bool = False


class CommunityCommentThreadData(CommunitySchema):
    id: UUID
    parent_id: None = None
    content: str
    author: CommunityAuthorData | None
    is_deleted: bool
    created_at: datetime
    like_count: int = 0
    viewer_has_liked: bool = False
    replies: list[CommunityCommentReplyData]


class CommunityMemberProfileEditRequest(CommunitySchema):
    username: Annotated[str | None, Field(max_length=64)] = None
    display_name: Annotated[str | None, Field(max_length=120)] = None
    avatar_url: Annotated[str | None, Field(max_length=500)] = None
    avatar_media_id: UUID | None = None
    bio: Annotated[str | None, Field(max_length=500)] = None

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        if value is None:
            raise ValueError("Username cannot be null.")
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        if not (
            re.fullmatch(r"[a-z0-9_-]{3,30}", normalized)
            or re.fullmatch(r"member-[0-9a-f]{32}", normalized)
        ):
            raise ValueError("Username must contain 3 to 30 safe characters.")
        if normalized in {
            "me",
            "posts",
            "bookmarks",
            "followers",
            "following",
            "admin",
        }:
            raise ValueError("This username is reserved.")
        return normalized

    @field_validator("display_name", "bio")
    @classmethod
    def normalize_profile_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = "".join(
            character
            for character in value.replace("\r\n", "\n").replace("\r", "\n")
            if character in "\n\t" or ord(character) >= 32
        ).strip()
        if _HTML_TAG.search(normalized):
            raise ValueError("HTML is not allowed in community profiles.")
        return normalized or None

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        parts = urlsplit(normalized)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
        ):
            raise ValueError("Avatar URL must be an HTTPS URL.")
        return normalized

    @model_validator(mode="after")
    def require_update_field(self) -> "CommunityMemberProfileEditRequest":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided.")
        return self


class CommunityMemberData(CommunitySchema):
    id: UUID
    username: str
    display_name: str
    avatar_url: str | None
    role_label: str | None
    is_admin: bool
    bio: str | None
    joined_at: datetime
    published_post_count: int
    follower_count: int
    following_count: int
    viewer_is_following: bool


class CommunityLikeStateData(CommunitySchema):
    post_id: UUID
    like_count: int
    is_liked: bool


class CommunityBookmarkStateData(CommunitySchema):
    post_id: UUID
    is_bookmarked: bool


class CommunityFollowStateData(CommunitySchema):
    member_id: UUID
    is_following: bool
    follower_count: int


class CommunityCommentLikeStateData(CommunitySchema):
    comment_id: UUID
    like_count: int
    is_liked: bool


class CommunityMemberListItemData(CommunitySchema):
    id: UUID
    username: str
    display_name: str
    avatar_url: str | None
    role_label: str | None
    is_admin: bool
    viewer_is_following: bool
