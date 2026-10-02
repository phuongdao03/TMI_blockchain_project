from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.notifications.admin_service import AnnouncementAudience


class NotificationData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=True
    )
    id: UUID
    type: str
    title: str
    body: str
    data_json: dict[str, object] = Field(alias="data")
    read_at: datetime | None = Field(alias="readAt")
    created_at: datetime = Field(alias="createdAt")


class UnreadCountData(BaseModel):
    unread_count: int = Field(alias="unreadCount")
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MarkAllReadData(BaseModel):
    updated_count: int = Field(alias="updatedCount")
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MarkReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    read: Literal[True]


class AnnouncementAudienceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    audience: AnnouncementAudience
    recipient_user_id: UUID | None = Field(default=None, alias="recipientUserId")


class AnnouncementSendRequest(AnnouncementAudienceRequest):
    campaign_id: UUID = Field(alias="campaignId")
    title: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=3, max_length=5000)

    @field_validator("title", "body")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 3:
            raise ValueError("Enter at least three non-space characters.")
        return stripped


class AnnouncementPreviewData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    recipient_count: int = Field(alias="recipientCount")


class AnnouncementSentData(AnnouncementPreviewData):
    campaign_id: UUID = Field(alias="campaignId")
