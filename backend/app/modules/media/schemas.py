from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.media.models import MediaConfidentiality, MediaStatus
from app.modules.media.types import MediaPurpose


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class MediaSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class UploadSignatureRequest(MediaSchema):
    purpose: MediaPurpose
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    mime_type: Annotated[str, Field(min_length=3, max_length=127)]
    size: Annotated[int, Field(gt=0)]
    confidentiality: MediaConfidentiality = MediaConfidentiality.PRIVATE

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        if (
            value != value.strip()
            or value in (".", "..")
            or "/" in value
            or "\\" in value
            or any(ord(character) < 32 for character in value)
        ):
            raise ValueError("Filename must be a plain file name.")
        return value


class CompleteUploadRequest(MediaSchema):
    media_id: UUID
    public_id: Annotated[str, Field(min_length=1, max_length=512)]
    version: Annotated[int, Field(ge=0)]
    signature: Annotated[str, Field(pattern=r"^[a-fA-F0-9]{40}$")]


class UploadSignatureData(MediaSchema):
    media_id: UUID
    public_id: str
    upload_url: str
    cloud_name: str
    api_key: str
    signature: str
    parameters: dict[str, str]
    expires_at: int


class MediaAssetData(MediaSchema):
    id: UUID
    status: MediaStatus
    mime_type: str
    bytes: int
    width: int | None
    height: int | None
    duration_ms: int | None
    inspection_attempts: int = 0
    inspection_reason_code: str | None = None
    inspected_at: datetime | None = None


class SignedDeliveryData(MediaSchema):
    url: str
    expires_at: int


class MediaActionData(MediaSchema):
    status: Literal["deleted"]
