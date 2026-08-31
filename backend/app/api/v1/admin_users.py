from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.errors import DomainError
from app.core.schemas import (
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
    SettingsDependency,
)
from app.modules.auth.firebase_admin_gateway import (
    FirebaseAdminError,
    FirebaseAdminGateway,
)
from app.modules.auth.models import AuthProvider, UserStatus
from app.modules.users.admin_service import (
    AdminUserData,
    AdminUserQuery,
    AdminUserService,
    AdminUserStatusRequest,
    SortField,
    SortOrder,
)

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin users"])


@router.get("", response_model=PaginatedSuccessEnvelope[list[AdminUserData]])
async def list_admin_users(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    status: UserStatus | None = None,
    provider: AuthProvider | None = None,
    verified: bool | None = None,
    created_from: Annotated[datetime | None, Query(alias="createdFrom")] = None,
    created_to: Annotated[datetime | None, Query(alias="createdTo")] = None,
    sort_by: Annotated[SortField, Query(alias="sortBy")] = "createdAt",
    sort_order: Annotated[SortOrder, Query(alias="sortOrder")] = "desc",
) -> PaginatedSuccessEnvelope[list[AdminUserData]]:
    try:
        query = AdminUserQuery(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            provider=provider,
            verified=verified,
            created_from=created_from,
            created_to=created_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as exc:
        raise DomainError(
            code="ADMIN_USER_QUERY_INVALID",
            message=str(exc),
            status_code=422,
        ) from exc
    rows, total = await AdminUserService(session).list(principal, query)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get("/{user_id}", response_model=SuccessEnvelope[AdminUserData])
async def admin_user_detail(
    user_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AdminUserData]:
    data = await AdminUserService(session).detail(principal, user_id)
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/{user_id}/status",
    response_model=SuccessEnvelope[AdminUserData],
)
async def change_admin_user_status(
    user_id: UUID,
    payload: AdminUserStatusRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[AdminUserData]:
    try:
        firebase_admin = FirebaseAdminGateway.create(settings)
    except FirebaseAdminError as exc:
        raise DomainError(
            code="FIREBASE_ADMIN_UNAVAILABLE",
            message="Firebase user administration is temporarily unavailable.",
            status_code=503,
        ) from exc
    data = await AdminUserService(
        session,
        firebase_admin=firebase_admin,
    ).change_status(
        principal,
        user_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )
