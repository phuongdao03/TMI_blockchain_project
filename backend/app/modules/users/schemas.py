from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class PatchUserProfileRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        extra="forbid",
    )

    full_name: Annotated[str | None, Field(min_length=1, max_length=255)] = None
    phone: Annotated[
        str | None,
        Field(pattern=r"^\+[1-9]\d{7,14}$"),
    ] = None
    avatar_media_id: UUID | None = None
    locale: Annotated[
        str | None,
        Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$", max_length=16),
    ] = None
    timezone: Annotated[str | None, Field(min_length=1, max_length=64)] = None

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Timezone must be a valid IANA timezone.") from exc
        return value

    @model_validator(mode="after")
    def require_non_null_preferences(self) -> "PatchUserProfileRequest":
        for field_name in ("locale", "timezone"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null.")
        return self


class UserProfileData(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )

    user_id: UUID
    email: EmailStr
    full_name: str | None
    phone: str | None
    avatar_media_id: UUID | None
    locale: str
    timezone: str
