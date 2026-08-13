from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.audit.models import AuditActorType, AuditLog
from app.modules.audit.service import AuditIntegrityStatus


class AuditLogData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=True
    )
    id: UUID
    actor_user_id: UUID | None = Field(alias="actorUserId")
    actor_type: AuditActorType = Field(alias="actorType")
    actor_service: str | None = Field(alias="actorService")
    action: str
    resource_type: str = Field(alias="resourceType")
    resource_id: str = Field(alias="resourceId")
    before_json: dict[str, object] | None = Field(alias="before")
    after_json: dict[str, object] | None = Field(alias="after")
    request_id: str | None = Field(alias="requestId")
    integrity_status: AuditIntegrityStatus = Field(alias="integrityStatus")
    retention_until: datetime | None = Field(alias="retentionUntil")
    created_at: datetime = Field(alias="createdAt")

    @classmethod
    def from_row(
        cls,
        row: AuditLog,
        *,
        integrity_status: AuditIntegrityStatus,
    ) -> "AuditLogData":
        return cls.model_validate(
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "actor_type": row.actor_type,
                "actor_service": row.actor_service,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "before_json": row.before_json,
                "after_json": row.after_json,
                "request_id": row.request_id,
                "integrity_status": integrity_status,
                "retention_until": row.retention_until,
                "created_at": row.created_at,
            }
        )


class AuditIntegrityCheckData(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda name: "".join(
            part.capitalize() if index else part
            for index, part in enumerate(name.split("_"))
        ),
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )

    scanned: int
    total: int
    is_complete: bool
    counts: dict[AuditIntegrityStatus, int]
