from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.modules.media.models import MediaConfidentiality, MediaStatus


class MediaPurpose(StrEnum):
    AVATAR = "AVATAR"
    DOSSIER_EVIDENCE = "DOSSIER_EVIDENCE"
    PUBLIC_WORK = "PUBLIC_WORK"


@dataclass(frozen=True, slots=True)
class UploadIntent:
    purpose: MediaPurpose
    filename: str
    mime_type: str
    size: int
    confidentiality: MediaConfidentiality = MediaConfidentiality.PRIVATE


@dataclass(frozen=True, slots=True)
class UploadCompletion:
    media_id: UUID
    public_id: str
    version: int
    signature: str


@dataclass(frozen=True, slots=True)
class UploadSignatureView:
    media_id: UUID
    public_id: str
    upload_url: str
    cloud_name: str
    api_key: str
    signature: str
    parameters: Mapping[str, str]
    expires_at: int


@dataclass(frozen=True, slots=True)
class MediaAssetView:
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


@dataclass(frozen=True, slots=True)
class SignedDeliveryView:
    url: str
    expires_at: int


@dataclass(frozen=True, slots=True)
class MediaContentView:
    content: bytes
    mime_type: str
    filename: str
