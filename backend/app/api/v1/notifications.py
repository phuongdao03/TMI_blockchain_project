from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.errors import DomainError
from app.core.schemas import (
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.notifications.dependencies import NotificationServiceDependency
from app.modules.notifications.schemas import (
    MarkAllReadData,
    MarkReadRequest,
    NotificationData,
    UnreadCountData,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedSuccessEnvelope[list[NotificationData]])
async def list_notifications(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: NotificationServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    unread_only: bool = Query(default=False, alias="unreadOnly"),
) -> PaginatedSuccessEnvelope[list[NotificationData]]:
    rows, total = await service.list(
        principal.user_id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    return PaginatedSuccessEnvelope(
        data=[NotificationData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.patch("/read-all", response_model=SuccessEnvelope[MarkAllReadData])
async def mark_all_read(
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: NotificationServiceDependency,
) -> SuccessEnvelope[MarkAllReadData]:
    updated = await service.mark_all_read(principal.user_id)
    return SuccessEnvelope(
        data=MarkAllReadData(updatedCount=updated),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/unread-count", response_model=SuccessEnvelope[UnreadCountData])
async def unread_count(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: NotificationServiceDependency,
) -> SuccessEnvelope[UnreadCountData]:
    count = await service.unread_count(principal.user_id)
    return SuccessEnvelope(
        data=UnreadCountData(unreadCount=count),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch("/{notification_id}", response_model=SuccessEnvelope[NotificationData])
async def mark_read(
    notification_id: UUID,
    payload: MarkReadRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: NotificationServiceDependency,
) -> SuccessEnvelope[NotificationData]:
    del payload
    row = await service.mark_read(
        user_id=principal.user_id, notification_id=notification_id
    )
    if row is None:
        raise DomainError(
            code="NOTIFICATION_NOT_FOUND",
            message="Notification was not found.",
            status_code=404,
        )
    return SuccessEnvelope(
        data=NotificationData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
