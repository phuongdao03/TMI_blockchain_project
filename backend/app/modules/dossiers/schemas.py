from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.dossiers.models import DossierStatus, DossierVisibility


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class DossierSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
        from_attributes=True,
    )


class CreateDossierRequest(DossierSchema):
    category_id: UUID
    organization_id: UUID | None = None
    title: Annotated[str, Field(min_length=1, max_length=255)]
    slug: Annotated[
        str | None,
        Field(max_length=280, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ] = None
    summary: Annotated[str | None, Field(max_length=10_000)] = None
    visibility: DossierVisibility = DossierVisibility.PRIVATE

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PatchDossierRequest(DossierSchema):
    category_id: UUID | None = None
    organization_id: UUID | None = None
    title: Annotated[str | None, Field(min_length=1, max_length=255)] = None
    slug: Annotated[
        str | None,
        Field(max_length=280, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ] = None
    summary: Annotated[str | None, Field(max_length=10_000)] = None
    visibility: DossierVisibility | None = None

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_patch(self) -> "PatchDossierRequest":
        if not self.model_fields_set:
            raise ValueError("At least one dossier field is required.")
        for field_name in ("category_id", "title", "visibility"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null.")
        return self


class DossierData(DossierSchema):
    id: UUID
    code: str
    owner_user_id: UUID
    organization_id: UUID | None
    category_id: UUID
    title: str
    slug: str | None
    summary: str | None
    status: DossierStatus
    visibility: DossierVisibility
    current_version_no: int
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_edit: bool


class DossierActionData(DossierSchema):
    status: Literal["deleted", "removed"]


class CreateEvidenceRequest(DossierSchema):
    media_asset_id: UUID
    evidence_type: Annotated[
        str,
        Field(min_length=2, max_length=64, pattern=r"^[A-Z][A-Z0-9_]+$"),
    ]
    title: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str | None, Field(max_length=10_000)] = None
    issued_at: datetime | None = None
    display_order: Annotated[int, Field(ge=0)] = 0
    is_public: bool = False

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PatchEvidenceRequest(DossierSchema):
    evidence_type: Annotated[
        str | None,
        Field(min_length=2, max_length=64, pattern=r"^[A-Z][A-Z0-9_]+$"),
    ] = None
    title: Annotated[str | None, Field(min_length=1, max_length=255)] = None
    description: Annotated[str | None, Field(max_length=10_000)] = None
    issued_at: datetime | None = None
    display_order: Annotated[int | None, Field(ge=0)] = None
    is_public: bool | None = None

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_patch(self) -> "PatchEvidenceRequest":
        if not self.model_fields_set:
            raise ValueError("At least one evidence field is required.")
        for field_name in (
            "evidence_type",
            "title",
            "display_order",
            "is_public",
        ):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null.")
        return self


class EvidenceData(DossierSchema):
    id: UUID
    dossier_id: UUID
    dossier_version_id: UUID | None
    media_asset_id: UUID
    evidence_type: str
    title: str
    description: str | None
    issued_at: datetime | None
    display_order: int
    is_public: bool
    mime_type: str
    bytes: int
    sha256: str


class DossierDetailData(DossierData):
    evidences: tuple[EvidenceData, ...]


class DossierVersionData(DossierSchema):
    id: UUID
    dossier_id: UUID
    version_no: int
    snapshot_json: dict[str, object]
    canonical_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    submitted_by: UUID
    submitted_at: datetime


class DossierStatusHistoryData(DossierSchema):
    id: UUID
    dossier_id: UUID
    from_status: DossierStatus
    to_status: DossierStatus
    actor_user_id: UUID
    reason_code: str | None
    note: str | None
    created_at: datetime


class SubmissionData(DossierSchema):
    dossier: DossierData
    version: DossierVersionData
