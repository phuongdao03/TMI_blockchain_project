from fastapi import APIRouter, Request

from app.core.errors import DomainError
from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    SessionDependency,
)
from app.modules.notifications.admin_service import AdminAnnouncementService
from app.modules.notifications.schemas import (
    AnnouncementAudienceRequest,
    AnnouncementPreviewData,
    AnnouncementSendRequest,
    AnnouncementSentData,
)

router = APIRouter(prefix="/api/v1/admin/notifications", tags=["admin notifications"])


def _require_super_admin(principal: CsrfProtectedPrincipalDependency) -> None:
    if "SUPER_ADMIN" not in principal.roles:
        raise DomainError(
            code="ANNOUNCEMENT_FORBIDDEN",
            message="Only a system administrator can send announcements.",
            status_code=403,
        )


@router.post("/preview", response_model=SuccessEnvelope[AnnouncementPreviewData])
async def preview_announcement(
    payload: AnnouncementAudienceRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AnnouncementPreviewData]:
    _require_super_admin(principal)
    count = await AdminAnnouncementService(session).preview(
        payload.audience, payload.recipient_user_id
    )
    return SuccessEnvelope(
        data=AnnouncementPreviewData(recipientCount=count),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("", response_model=SuccessEnvelope[AnnouncementSentData])
async def send_announcement(
    payload: AnnouncementSendRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AnnouncementSentData]:
    _require_super_admin(principal)
    count = await AdminAnnouncementService(session).send(
        audience=payload.audience,
        recipient_user_id=payload.recipient_user_id,
        campaign_id=payload.campaign_id,
        title=payload.title,
        body=payload.body,
        actor_user_id=principal.user_id,
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=AnnouncementSentData(campaignId=payload.campaign_id, recipientCount=count),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
