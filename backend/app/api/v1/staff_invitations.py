from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.core.schemas import (
    ErrorEnvelope,
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
    StaffInvitationServiceDependency,
)
from app.modules.auth.schemas import StaffInvitationData, StaffInvitationRequest

router = APIRouter(
    prefix="/api/v1/admin/staff-invitations",
    tags=["staff invitations"],
)

ADMIN_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Administrator access is required.", "model": ErrorEnvelope},
}


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[StaffInvitationData]],
    responses=ADMIN_ERROR_RESPONSES,
)
async def list_staff_invitations(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: StaffInvitationServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[StaffInvitationData]]:
    service.require_super_admin(principal)
    rows, total = await service.list(page=page, page_size=page_size)
    return PaginatedSuccessEnvelope(
        data=rows,
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[StaffInvitationData],
    responses=ADMIN_ERROR_RESPONSES,
)
async def create_staff_invitation(
    payload: StaffInvitationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: StaffInvitationServiceDependency,
    session: SessionDependency,
) -> SuccessEnvelope[StaffInvitationData]:
    result = await service.create(
        payload=payload,
        principal=principal,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=result,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{invitation_id}/resend",
    response_model=SuccessEnvelope[StaffInvitationData],
    responses=ADMIN_ERROR_RESPONSES,
)
async def resend_staff_invitation(
    invitation_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: StaffInvitationServiceDependency,
    session: SessionDependency,
) -> SuccessEnvelope[StaffInvitationData]:
    result = await service.resend(
        invitation_id=invitation_id,
        principal=principal,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=result,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{invitation_id}/revoke",
    response_model=SuccessEnvelope[StaffInvitationData],
    responses=ADMIN_ERROR_RESPONSES,
)
async def revoke_staff_invitation(
    invitation_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: StaffInvitationServiceDependency,
    session: SessionDependency,
) -> SuccessEnvelope[StaffInvitationData]:
    result = await service.revoke(
        invitation_id=invitation_id,
        principal=principal,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=result,
        meta=ResponseMeta(request_id=request.state.request_id),
    )
