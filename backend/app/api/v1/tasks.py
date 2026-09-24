from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

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
from app.modules.tasks.models import TaskPriority, TaskStatus
from app.modules.tasks.schemas import (
    AddTaskAttachmentRequest,
    CreateTaskChecklistItemRequest,
    CreateTaskCommentRequest,
    CreateTaskRequest,
    TaskActivityData,
    TaskAttachmentData,
    TaskChecklistItemData,
    TaskCommentData,
    TaskData,
    UpdateTaskChecklistItemRequest,
    UpdateTaskRequest,
)
from app.modules.tasks.service import TaskService

router = APIRouter(prefix="/api/v1/admin/tasks", tags=["tasks"])


@router.get("", response_model=PaginatedSuccessEnvelope[list[TaskData]])
async def list_tasks(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=240)] = None,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    sort_by: Annotated[Literal["createdAt", "dueAt"], Query(alias="sortBy")] = (
        "createdAt"
    ),
    sort_direction: Annotated[Literal["asc", "desc"], Query(alias="sortDirection")] = (
        "desc"
    ),
) -> PaginatedSuccessEnvelope[list[TaskData]]:
    rows, total = await TaskService(session).list_tasks(
        principal,
        page=page,
        page_size=page_size,
        search=search,
        task_status=task_status,
        priority=priority,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
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
    response_model=SuccessEnvelope[TaskData],
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    payload: CreateTaskRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[TaskData]:
    data = await TaskService(session).create_task(
        principal,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/{task_id}", response_model=SuccessEnvelope[TaskData])
async def get_task(
    task_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[TaskData]:
    data = await TaskService(session).get_task(principal, task_id)
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch("/{task_id}", response_model=SuccessEnvelope[TaskData])
async def update_task(
    task_id: UUID,
    payload: UpdateTaskRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[TaskData]:
    data = await TaskService(session).update_task(
        principal,
        task_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{task_id}/checklist-items",
    response_model=SuccessEnvelope[list[TaskChecklistItemData]],
)
async def list_checklist_items(
    task_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[TaskChecklistItemData]]:
    data = await TaskService(session).list_checklist_items(principal, task_id)
    return SuccessEnvelope(
        data=list(data),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{task_id}/checklist-items",
    response_model=SuccessEnvelope[TaskChecklistItemData],
    status_code=status.HTTP_201_CREATED,
)
async def create_checklist_item(
    task_id: UUID,
    payload: CreateTaskChecklistItemRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[TaskChecklistItemData]:
    data = await TaskService(session).create_checklist_item(
        principal,
        task_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/{task_id}/checklist-items/{checklist_item_id}",
    response_model=SuccessEnvelope[TaskChecklistItemData],
)
async def update_checklist_item(
    task_id: UUID,
    checklist_item_id: UUID,
    payload: UpdateTaskChecklistItemRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[TaskChecklistItemData]:
    data = await TaskService(session).update_checklist_item(
        principal,
        task_id,
        checklist_item_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{task_id}/comments",
    response_model=PaginatedSuccessEnvelope[list[TaskCommentData]],
)
async def list_comments(
    task_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[TaskCommentData]]:
    rows, total = await TaskService(session).list_comments(
        principal,
        task_id,
        page=page,
        page_size=page_size,
    )
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
    "/{task_id}/comments",
    response_model=SuccessEnvelope[TaskCommentData],
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    task_id: UUID,
    payload: CreateTaskCommentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[TaskCommentData]:
    data = await TaskService(session).create_comment(
        principal,
        task_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{task_id}/attachments",
    response_model=SuccessEnvelope[list[TaskAttachmentData]],
)
async def list_attachments(
    task_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[list[TaskAttachmentData]]:
    data = await TaskService(session).list_attachments(principal, task_id)
    return SuccessEnvelope(
        data=list(data),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{task_id}/attachments",
    response_model=SuccessEnvelope[TaskAttachmentData],
    status_code=status.HTTP_201_CREATED,
)
async def add_attachment(
    task_id: UUID,
    payload: AddTaskAttachmentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[TaskAttachmentData]:
    data = await TaskService(session).add_attachment(
        principal,
        task_id,
        payload,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{task_id}/activities",
    response_model=PaginatedSuccessEnvelope[list[TaskActivityData]],
)
async def list_activities(
    task_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[TaskActivityData]]:
    rows, total = await TaskService(session).list_activities(
        principal,
        task_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=list(rows),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )
