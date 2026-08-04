from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class MarkReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    read: Literal[True]
