from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class SupplementSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="forbid",
    )


class SupplementResponseData(SupplementSchema):
    id: UUID
    sequence_no: int
    kind: Literal["RESPONSE", "RESOLVE", "REOPEN"]
    text: str
    created_at: datetime


class SupplementData(SupplementSchema):
    id: UUID
    dossier_id: UUID
    requested_version_id: UUID
    criterion_key: str
    criterion_label: str
    claim_id: UUID | None
    requested_information: str
    reason: str
    priority: Literal["NORMAL", "HIGH"]
    due_at: datetime | None
    created_at: datetime
    status: Literal["OPEN", "ANSWERED", "RESOLVED"]
    revision: int
    responses: tuple[SupplementResponseData, ...]


class CreateSupplementRequest(SupplementSchema):
    expected_version_id: UUID
    criterion_key: Annotated[str, Field(min_length=1, max_length=64)]
    claim_id: UUID | None = None
    requested_information: Annotated[str, Field(min_length=20, max_length=2000)]
    reason: Annotated[str, Field(min_length=20, max_length=2000)]
    priority: Literal["NORMAL", "HIGH"] = "NORMAL"
    due_at: datetime | None = None


class RespondSupplementRequest(SupplementSchema):
    expected_revision: Annotated[int, Field(ge=0)]
    text: Annotated[str, Field(min_length=20, max_length=2000)]


class ResolveSupplementRequest(SupplementSchema):
    expected_revision: Annotated[int, Field(ge=0)]
    resolution: Annotated[str, Field(min_length=20, max_length=2000)]
    reopen: bool = False
