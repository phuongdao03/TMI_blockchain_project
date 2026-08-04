from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=True
    )
    id: UUID
    actor_user_id: UUID | None = Field(alias="actorUserId")
    action: str
    resource_type: str = Field(alias="resourceType")
    resource_id: str = Field(alias="resourceId")
    before_json: dict[str, object] | None = Field(alias="before")
    after_json: dict[str, object] | None = Field(alias="after")
    request_id: str | None = Field(alias="requestId")
    created_at: datetime = Field(alias="createdAt")
