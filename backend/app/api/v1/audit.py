import csv
import io
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.core.errors import DomainError
from app.core.schemas import (
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.audit.dependencies import AuditServiceDependency
from app.modules.audit.schemas import AuditIntegrityCheckData, AuditLogData
from app.modules.audit.service import AuditIntegrityStatus
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.auth.session_service import AuthPrincipal

router = APIRouter(prefix="/api/v1/admin/audit", tags=["audit"])
AUDIT_EXPORT_MAX_ROWS = 10_000
AUDIT_INTEGRITY_SCAN_MAX_ROWS = 10_000


def require_audit_access(principal: AuthPrincipal) -> None:
    AuthorizationPolicy.require_capability(
        principal,
        PolicyRequirement(
            permission="audit.read", compatible_roles=frozenset({"SUPER_ADMIN"})
        ),
        lambda: DomainError(
            code="AUDIT_FORBIDDEN",
            message="Audit access is forbidden.",
            status_code=403,
        ),
    )


def _validate_date_range(
    created_from: datetime | None,
    created_to: datetime | None,
) -> None:
    if (
        created_from is not None
        and created_to is not None
        and created_from > created_to
    ):
        raise DomainError(
            code="AUDIT_DATE_RANGE_INVALID",
            message="Audit date range is invalid.",
            status_code=422,
        )


def _csv_safe(value: object | None) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@router.get("", response_model=PaginatedSuccessEnvelope[list[AuditLogData]])
async def search_audit(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    service: AuditServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    actor_user_id: Annotated[UUID | None, Query(alias="actorUserId")] = None,
    action: str | None = Query(default=None, max_length=128),
    resource_type: str | None = Query(
        default=None, alias="resourceType", max_length=64
    ),
    created_from: Annotated[datetime | None, Query(alias="createdFrom")] = None,
    created_to: Annotated[datetime | None, Query(alias="createdTo")] = None,
) -> PaginatedSuccessEnvelope[list[AuditLogData]]:
    require_audit_access(principal)
    _validate_date_range(created_from, created_to)
    async with session.begin():
        rows, total = await service.search(
            page=page,
            page_size=page_size,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            created_from=created_from,
            created_to=created_to,
        )
        service.record(
            actor_user_id=principal.user_id,
            action="audit.read",
            resource_type="audit_log",
            resource_id="search",
            after={
                "page": page,
                "page_size": page_size,
                "result_count": len(rows),
                "filters_applied": any(
                    value is not None
                    for value in (
                        actor_user_id,
                        action,
                        resource_type,
                        created_from,
                        created_to,
                    )
                ),
            },
            request_id=request.state.request_id,
            user_agent=request.headers.get("user-agent"),
        )
    return PaginatedSuccessEnvelope(
        data=[
            AuditLogData.from_row(
                row,
                integrity_status=service.verify_integrity(row),
            )
            for row in rows
        ],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get("/exports.csv", response_class=Response)
async def export_audit(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    service: AuditServiceDependency,
    limit: int = Query(default=1_000, ge=1, le=AUDIT_EXPORT_MAX_ROWS),
    actor_user_id: Annotated[UUID | None, Query(alias="actorUserId")] = None,
    action: str | None = Query(default=None, max_length=128),
    resource_type: str | None = Query(
        default=None, alias="resourceType", max_length=64
    ),
    created_from: Annotated[datetime | None, Query(alias="createdFrom")] = None,
    created_to: Annotated[datetime | None, Query(alias="createdTo")] = None,
) -> Response:
    require_audit_access(principal)
    _validate_date_range(created_from, created_to)
    async with session.begin():
        rows, total = await service.search(
            page=1,
            page_size=limit,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            created_from=created_from,
            created_to=created_to,
        )
        service.record(
            actor_user_id=principal.user_id,
            action="audit.exported",
            resource_type="audit_log",
            resource_id="csv",
            after={
                "requested_limit": limit,
                "exported_count": len(rows),
                "total_available": total,
            },
            request_id=request.state.request_id,
            user_agent=request.headers.get("user-agent"),
        )

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        (
            "created_at",
            "id",
            "actor_type",
            "actor_reference",
            "action",
            "resource_type",
            "resource_id",
            "request_id",
            "integrity_status",
            "retention_until",
        )
    )
    for row in rows:
        actor_reference = row.actor_user_id or row.actor_service
        writer.writerow(
            (
                row.created_at.isoformat(),
                row.id,
                row.actor_type.value,
                _csv_safe(actor_reference),
                _csv_safe(row.action),
                _csv_safe(row.resource_type),
                _csv_safe(row.resource_id),
                _csv_safe(row.request_id),
                service.verify_integrity(row).value,
                row.retention_until.isoformat() if row.retention_until else "",
            )
        )
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": "attachment; filename=audit-export.csv",
        },
    )


@router.post(
    "/integrity-checks",
    response_model=SuccessEnvelope[AuditIntegrityCheckData],
)
async def check_audit_integrity(
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    service: AuditServiceDependency,
    limit: int = Query(default=1_000, ge=1, le=AUDIT_INTEGRITY_SCAN_MAX_ROWS),
) -> SuccessEnvelope[AuditIntegrityCheckData]:
    require_audit_access(principal)
    async with session.begin():
        rows, total = await service.search(page=1, page_size=limit)
        counts = {status: 0 for status in AuditIntegrityStatus}
        for row in rows:
            counts[service.verify_integrity(row)] += 1
        service.record(
            actor_user_id=principal.user_id,
            action="audit.integrity_checked",
            resource_type="audit_log",
            resource_id="integrity",
            after={
                "requested_limit": limit,
                "scanned": len(rows),
                "total": total,
                "is_complete": len(rows) >= total,
                "tampered_count": counts[AuditIntegrityStatus.TAMPERED],
            },
            request_id=request.state.request_id,
            user_agent=request.headers.get("user-agent"),
        )
    return SuccessEnvelope(
        data=AuditIntegrityCheckData(
            scanned=len(rows),
            total=total,
            is_complete=len(rows) >= total,
            counts=counts,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
