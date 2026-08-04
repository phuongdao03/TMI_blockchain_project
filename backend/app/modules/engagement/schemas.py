from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.engagement.activity import ActivityKind


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class FavoriteData(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )

    favorite_id: UUID
    public_work_id: UUID
    slug: str
    title: str
    short_description: str
    created_at: datetime


class ShareChannel(StrEnum):
    NATIVE = "NATIVE"
    COPY_LINK = "COPY_LINK"


class ShareActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: ShareChannel


class ShareActionAcceptedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool


class ActivityData(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )

    activity_id: UUID
    kind: ActivityKind
    public_work_id: UUID
    slug: str
    title: str
    short_description: str
    channel: ShareChannel | None
    created_at: datetime


class ActivityPageData(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )

    items: list[ActivityData]
    next_cursor: str | None
