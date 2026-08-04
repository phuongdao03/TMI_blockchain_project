from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.errors import DomainError
from app.core.schemas import ListResponseMeta, PaginatedSuccessEnvelope
from app.modules.audit.repository import AuditRepository
from app.modules.audit.schemas import AuditLogData
from app.modules.auth.dependencies import CurrentPrincipalDependency, SessionDependency

router = APIRouter(prefix="/api/v1/admin/audit", tags=["audit"])


@router.get("", response_model=PaginatedSuccessEnvelope[list[AuditLogData]])
async def search_audit(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    actor_user_id: Annotated[UUID | None, Query(alias="actorUserId")] = None,
    action: str | None = Query(default=None, max_length=128),
    resource_type: str | None = Query(
        default=None, alias="resourceType", max_length=64
    ),
) -> PaginatedSuccessEnvelope[list[AuditLogData]]:
    if "SUPER_ADMIN" not in principal.roles:
        raise DomainError(
            code="AUDIT_FORBIDDEN",
            message="Audit access is forbidden.",
            status_code=403,
        )
    async with session.begin():
        rows, total = await AuditRepository(session).list(
            page=page,
            page_size=page_size,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
        )
    return PaginatedSuccessEnvelope(
        data=[AuditLogData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )
