from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response, status

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
)
from app.modules.work_allocations.schemas import (
    ActivateWorkAllocationRequest,
    CreateWorkAllocationRequest,
    WorkAllocationData,
    WorkAllocationDetailData,
)
from app.modules.work_allocations.service import WorkAllocationService

router = APIRouter(prefix="/api/v1/admin/work-allocations", tags=["work allocations"])
self_router = APIRouter(prefix="/api/v1/me/work-allocations", tags=["work allocations"])


def _private_response(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("", response_model=PaginatedSuccessEnvelope[list[WorkAllocationData]])
async def list_work_allocations(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[WorkAllocationData]]:
    rows, total = await WorkAllocationService(session).list_allocations(
        principal,
        page=page,
        page_size=page_size,
    )
    _private_response(response)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "",
    response_model=SuccessEnvelope[WorkAllocationData],
    status_code=status.HTTP_201_CREATED,
)
async def create_work_allocation(
    payload: CreateWorkAllocationRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[WorkAllocationData]:
    data = await WorkAllocationService(session).create_allocation(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_response(response)
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{allocation_id}",
    response_model=SuccessEnvelope[WorkAllocationDetailData],
)
async def get_work_allocation(
    allocation_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[WorkAllocationDetailData]:
    data = await WorkAllocationService(session).get_allocation(principal, allocation_id)
    _private_response(response)
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{allocation_id}/activate",
    response_model=SuccessEnvelope[WorkAllocationData],
)
async def activate_work_allocation(
    allocation_id: UUID,
    payload: ActivateWorkAllocationRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[WorkAllocationData]:
    data = await WorkAllocationService(session).activate_allocation(
        principal,
        allocation_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    _private_response(response)
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@self_router.get("", response_model=PaginatedSuccessEnvelope[list[WorkAllocationData]])
async def list_my_work_allocations(
    request: Request,
    response: Response,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[WorkAllocationData]]:
    rows, total = await WorkAllocationService(session).list_my_allocations(
        principal,
        page=page,
        page_size=page_size,
    )
    _private_response(response)
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )
