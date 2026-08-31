from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

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
)
from app.modules.auth.schemas import (
    PrivilegedActionData,
    PrivilegedActionRequest,
    StaffAccountData,
    StaffAccountRole,
    StaffAccountStatus,
    StaffAccountUpdateRequest,
    StaffMfaRecoveryRequest,
    StaffPermissionData,
    StaffPermissionReplaceRequest,
)
from app.modules.auth.staff_account_service import StaffAccountService
from app.modules.auth.staff_privileged_action_service import (
    StaffPrivilegedActionService,
)

router = APIRouter(prefix="/api/v1/admin/staff-accounts", tags=["staff accounts"])


def _service(session: SessionDependency) -> StaffAccountService:
    return StaffAccountService(session)


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[StaffAccountData]],
    responses={
        403: {
            "description": "Only super administrators can list staff.",
            "model": ErrorEnvelope,
        }
    },
)
async def list_staff_accounts(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    query: Annotated[str | None, Query(max_length=120)] = None,
    role: Annotated[StaffAccountRole | None, Query()] = None,
    account_status: Annotated[StaffAccountStatus | None, Query(alias="status")] = None,
) -> PaginatedSuccessEnvelope[list[StaffAccountData]]:
    service = _service(session)
    service.require_super_admin(principal)
    rows, total = await service.list(
        page=page,
        page_size=page_size,
        query=query,
        role=role,
        status=account_status,
    )
    return PaginatedSuccessEnvelope(
        data=rows,
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.patch(
    "/{user_id}",
    response_model=SuccessEnvelope[StaffAccountData],
    responses={
        403: {
            "description": "Only a super administrator can update staff.",
            "model": ErrorEnvelope,
        },
        404: {
            "description": "Staff account not found.",
            "model": ErrorEnvelope,
        },
    },
)
async def update_staff_account(
    user_id: UUID,
    payload: StaffAccountUpdateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[StaffAccountData]:
    data = await _service(session).update(
        user_id=user_id,
        payload=payload,
        principal=principal,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{user_id}/permissions",
    response_model=SuccessEnvelope[StaffPermissionData],
)
async def get_staff_permissions(
    user_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[StaffPermissionData]:
    data = await _service(session).get_permissions(user_id, principal)
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/{user_id}/permissions",
    response_model=SuccessEnvelope[StaffPermissionData],
)
async def replace_staff_permissions(
    user_id: UUID,
    payload: StaffPermissionReplaceRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[StaffPermissionData]:
    data = await _service(session).replace_permissions(
        user_id=user_id,
        payload=payload,
        principal=principal,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{user_id}/mfa-recovery",
    response_model=SuccessEnvelope[PrivilegedActionData],
    responses={
        403: {
            "description": "Only a super administrator can initiate recovery.",
            "model": ErrorEnvelope,
        },
        404: {"description": "Staff account not found.", "model": ErrorEnvelope},
    },
)
async def initiate_staff_mfa_recovery(
    user_id: UUID,
    payload: StaffMfaRecoveryRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PrivilegedActionData]:
    data = await StaffPrivilegedActionService(session=session).request(
        target_user_id=user_id,
        payload=PrivilegedActionRequest(
            action="MFA_RECOVERY",
            reason=payload.reason,
        ),
        principal=principal,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{user_id}/privileged-actions",
    response_model=SuccessEnvelope[PrivilegedActionData],
)
async def request_staff_privileged_action(
    user_id: UUID,
    payload: PrivilegedActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PrivilegedActionData]:
    data = await StaffPrivilegedActionService(session=session).request(
        target_user_id=user_id,
        payload=payload,
        principal=principal,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/privileged-actions/pending",
    response_model=PaginatedSuccessEnvelope[list[PrivilegedActionData]],
)
async def list_pending_staff_privileged_actions(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[PrivilegedActionData]]:
    rows, total = await StaffPrivilegedActionService(session=session).list_pending(
        principal=principal, page=page, page_size=page_size
    )
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
    "/privileged-actions/{action_id}/approve",
    response_model=SuccessEnvelope[PrivilegedActionData],
)
async def approve_staff_privileged_action(
    action_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[PrivilegedActionData]:
    data = await StaffPrivilegedActionService(session=session).approve(
        action_id=action_id,
        principal=principal,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )
