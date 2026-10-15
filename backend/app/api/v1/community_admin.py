from datetime import UTC, datetime
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.schemas import (
    ErrorEnvelope,
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.community.admin_repository import (
    CommunityAdminCommentRow,
    CommunityModerationEventRow,
    CommunityReportRow,
    CommunityRestrictionRow,
)
from app.modules.community.admin_schemas import (
    CommunityActionRequest,
    CommunityAdminActiveRestriction,
    CommunityAdminCategoryData,
    CommunityAdminCommentPostData,
    CommunityAdminCommentStateData,
    CommunityAdminCommentWorkspaceData,
    CommunityAdminMemberCard,
    CommunityAdminMemberWorkspaceData,
    CommunityAdminPostDeletionData,
    CommunityAdminPostLockData,
    CommunityAdminPostPinData,
    CommunityAdminSettingsData,
    CommunityCategoryCreateRequest,
    CommunityCategoryPatchRequest,
    CommunityMemberRestrictionCreateRequest,
    CommunityMemberRestrictionData,
    CommunityMemberRestrictionRevokeRequest,
    CommunityModerationEventData,
    CommunityModerationStateData,
    CommunityReportCommentPreview,
    CommunityReportData,
    CommunityReportPostPreview,
    CommunityReportRequest,
    CommunityReportResolutionRequest,
    CommunitySettingsRequest,
)
from app.modules.community.dependencies import CommunityAdminServiceDependency
from app.modules.community.models import CommunityReportReason
from app.modules.community.rate_limit import (
    enforce_community_content_write_rate_limit,
    enforce_community_report_write_rate_limit,
)
from app.modules.community.schemas import CommunityAuthorData

router = APIRouter(prefix="/api/v1/community", tags=["community-reports"])
admin_router = APIRouter(prefix="/api/v1/admin/community", tags=["community-admin"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Community action is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Community content was not found.", "model": ErrorEnvelope},
    409: {"description": "Community state conflict.", "model": ErrorEnvelope},
    422: {"description": "Community request is invalid.", "model": ErrorEnvelope},
}
_DELETED_COMMENT = "Bình luận đã bị xóa."
_HIDDEN_COMMENT = "Bình luận đã bị ẩn."


def _author(
    user_id: UUID,
    username: str | None,
    display_name: str | None,
    avatar_url: str | None,
) -> CommunityAuthorData:
    return CommunityAuthorData(
        id=user_id,
        username=username or f"member-{user_id.hex}",
        display_name=display_name or "Thành viên",
        avatar_url=avatar_url,
    )


def _report_data(row: CommunityReportRow) -> CommunityReportData:
    report = row.report
    reporter = _author(
        report.reporter_user_id,
        row.reporter_username,
        row.reporter_display_name,
        row.reporter_avatar_url,
    )
    preview: CommunityReportPostPreview | CommunityReportCommentPreview
    if row.post is not None:
        post = row.post
        preview = CommunityReportPostPreview(
            type="POST",
            id=post.id,
            slug=post.slug,
            title=post.title,
            excerpt=post.excerpt,
            author=_author(
                post.author_user_id,
                row.post_author_username,
                row.post_author_display_name,
                row.post_author_avatar_url,
            ),
        )
        target_type: Literal["POST", "COMMENT"] = "POST"
        target_id = post.id
    else:
        comment = row.comment
        comment_post = row.comment_post
        if comment is None or comment_post is None:
            raise ValueError("Report target is missing despite foreign key integrity.")
        is_deleted = (
            comment.deleted_at is not None or comment.moderation_hidden_at is not None
        )
        preview = CommunityReportCommentPreview(
            type="COMMENT",
            id=comment.id,
            post_id=comment_post.id,
            post_slug=comment_post.slug,
            post_title=comment_post.title,
            content=(
                _DELETED_COMMENT
                if comment.deleted_at is not None
                else _HIDDEN_COMMENT
                if comment.moderation_hidden_at is not None
                else comment.content
            ),
            is_deleted=is_deleted,
            author=(
                None
                if is_deleted
                else _author(
                    comment.author_user_id,
                    row.comment_author_username,
                    row.comment_author_display_name,
                    row.comment_author_avatar_url,
                )
            ),
        )
        target_type = "COMMENT"
        target_id = comment.id
    return CommunityReportData(
        id=report.id,
        target_type=target_type,
        target_id=target_id,
        status=cast(Literal["OPEN", "RESOLVED", "DISMISSED"], report.status),
        reason=cast(CommunityReportReason, report.reason),
        details=report.details,
        created_at=report.created_at,
        resolved_at=report.resolved_at,
        resolution_action=cast(
            Literal["HIDE", "DISMISS"] | None, report.resolution_action
        ),
        resolution_reason=report.resolution_reason,
        reporter=reporter,
        target_preview=preview,
    )


def _event_data(row: CommunityModerationEventRow) -> CommunityModerationEventData:
    event = row.event
    return CommunityModerationEventData(
        id=event.id,
        target_type=cast(
            Literal["POST", "COMMENT", "MEMBER", "CATEGORY", "SETTINGS"],
            event.target_type,
        ),
        target_id=event.target_id,
        action=event.action,
        actor_id=event.actor_user_id,
        actor=_author(
            event.actor_user_id,
            row.actor_username,
            row.actor_display_name,
            row.actor_avatar_url,
        ),
        reason=event.reason,
        request_id=event.request_id,
        created_at=event.created_at,
        metadata=event.event_data,
    )


def _admin_comment_data(
    row: CommunityAdminCommentRow,
) -> CommunityAdminCommentWorkspaceData:
    comment = row.comment
    deleted = comment.deleted_at is not None
    author = _author(
        comment.author_user_id,
        row.author_username,
        row.author_display_name,
        row.author_avatar_url,
    )
    return CommunityAdminCommentWorkspaceData(
        id=comment.id,
        post_id=comment.post_id,
        parent_id=comment.parent_id,
        content=comment.content,
        author=author,
        is_deleted=deleted,
        created_at=comment.created_at,
        like_count=row.like_count,
        viewer_has_liked=False,
        visibility=(
            "DELETED"
            if deleted
            else "HIDDEN"
            if comment.moderation_hidden_at is not None
            else "VISIBLE"
        ),
        post=CommunityAdminCommentPostData(
            id=row.post.id,
            slug=row.post.slug,
            title=row.post.title,
        ),
    )


def _admin_member_card(
    member_id: UUID,
    username: str | None,
    display_name: str | None,
    avatar_url: str | None,
) -> CommunityAdminMemberCard:
    return CommunityAdminMemberCard(
        id=member_id,
        username=username or f"member-{member_id.hex}",
        display_name=display_name or "Thành viên",
        avatar_url=avatar_url,
    )


def _restriction_data(row: CommunityRestrictionRow) -> CommunityMemberRestrictionData:
    restriction = row.restriction
    return CommunityMemberRestrictionData(
        id=restriction.id,
        member=_admin_member_card(
            restriction.member_user_id,
            row.member_username,
            row.member_display_name,
            row.member_avatar_url,
        ),
        scope=cast(Literal["POSTS", "COMMENTS"], restriction.scope),
        status=cast(Literal["ACTIVE", "EXPIRED", "REVOKED"], row.status),
        reason=restriction.reason,
        starts_at=_as_utc(restriction.starts_at),
        expires_at=_as_utc(restriction.expires_at),
        actor=_author(
            restriction.actor_user_id,
            row.actor_username,
            row.actor_display_name,
            row.actor_avatar_url,
        ),
        request_id=restriction.request_id,
    )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@router.post(
    "/posts/{post_id}/reports",
    dependencies=[Depends(enforce_community_report_write_rate_limit)],
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CommunityReportData],
    responses=PRIVATE_RESPONSES,
)
async def report_post(
    post_id: UUID,
    payload: CommunityReportRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityReportData]:
    result = await service.report_post(
        principal,
        post_id,
        payload,
        request_id=request.state.request_id,
    )
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return SuccessEnvelope(
        data=_report_data(result.row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/comments/{comment_id}/reports",
    dependencies=[Depends(enforce_community_report_write_rate_limit)],
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CommunityReportData],
    responses=PRIVATE_RESPONSES,
)
async def report_comment(
    comment_id: UUID,
    payload: CommunityReportRequest,
    request: Request,
    response: Response,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityReportData]:
    result = await service.report_comment(
        principal,
        comment_id,
        payload,
        request_id=request.state.request_id,
    )
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return SuccessEnvelope(
        data=_report_data(result.row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/reports",
    response_model=PaginatedSuccessEnvelope[list[CommunityReportData]],
    responses=PRIVATE_RESPONSES,
)
async def list_reports(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityAdminServiceDependency,
    report_status: Annotated[
        Literal["OPEN", "RESOLVED", "DISMISSED"], Query(alias="status")
    ] = "OPEN",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityReportData]]:
    result = await service.list_reports(
        principal,
        status=report_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_report_data(row) for row in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@admin_router.post(
    "/reports/{report_id}/resolve",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityReportData],
    responses=PRIVATE_RESPONSES,
)
async def resolve_report(
    report_id: UUID,
    payload: CommunityReportResolutionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityReportData]:
    row = await service.resolve_report(
        principal,
        report_id,
        payload,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=_report_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


async def _post_visibility(
    post_id: UUID,
    visible: bool,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityModerationStateData]:
    state_value = await service.set_post_visibility(
        principal,
        post_id,
        visible=visible,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityModerationStateData(
            target_type="POST",
            target_id=post_id,
            state=cast(Literal["HIDDEN", "VISIBLE"], state_value),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/posts/{post_id}/hide",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityModerationStateData],
    responses=PRIVATE_RESPONSES,
)
async def hide_post(
    post_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityModerationStateData]:
    return await _post_visibility(post_id, False, payload, request, principal, service)


@admin_router.post(
    "/posts/{post_id}/restore",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[
        CommunityModerationStateData | CommunityAdminPostDeletionData
    ],
    responses=PRIVATE_RESPONSES,
)
async def restore_post(
    post_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityModerationStateData | CommunityAdminPostDeletionData]:
    was_admin_deleted, restored_state = await service.restore_post_moderation_state(
        principal,
        post_id,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    if was_admin_deleted:
        data: CommunityModerationStateData | CommunityAdminPostDeletionData = (
            CommunityAdminPostDeletionData(
                post_id=post_id,
                is_deleted=False,
                deleted_at=None,
                restored_status=restored_state,
            )
        )
    else:
        data = CommunityModerationStateData(
            target_type="POST",
            target_id=post_id,
            state="VISIBLE",
        )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


async def _comment_visibility(
    comment_id: UUID,
    visible: bool,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminCommentStateData]:
    state_value = await service.set_comment_visibility(
        principal,
        comment_id,
        visible=visible,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminCommentStateData(
            comment_id=comment_id,
            visibility=cast(Literal["VISIBLE", "HIDDEN", "DELETED"], state_value),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/comments/{comment_id}/hide",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminCommentStateData],
    responses=PRIVATE_RESPONSES,
)
async def hide_comment(
    comment_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminCommentStateData]:
    return await _comment_visibility(
        comment_id, False, payload, request, principal, service
    )


@admin_router.post(
    "/comments/{comment_id}/restore",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminCommentStateData],
    responses=PRIVATE_RESPONSES,
)
async def restore_comment(
    comment_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminCommentStateData]:
    return await _comment_visibility(
        comment_id, True, payload, request, principal, service
    )


@admin_router.post(
    "/posts/{post_id}/pin",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminPostPinData],
    responses=PRIVATE_RESPONSES,
)
async def pin_post(
    post_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminPostPinData]:
    is_pinned = await service.set_post_pinned(
        principal,
        post_id,
        pinned=True,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminPostPinData(post_id=post_id, is_pinned=is_pinned),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/posts/{post_id}/unpin",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminPostPinData],
    responses=PRIVATE_RESPONSES,
)
async def unpin_post(
    post_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminPostPinData]:
    is_pinned = await service.set_post_pinned(
        principal,
        post_id,
        pinned=False,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminPostPinData(post_id=post_id, is_pinned=is_pinned),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/posts/{post_id}/comments/lock",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminPostLockData],
    responses=PRIVATE_RESPONSES,
)
async def lock_post_comments(
    post_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminPostLockData]:
    locked = await service.set_comments_locked(
        principal,
        post_id,
        locked=True,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminPostLockData(post_id=post_id, comments_locked=locked),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/posts/{post_id}/comments/unlock",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminPostLockData],
    responses=PRIVATE_RESPONSES,
)
async def unlock_post_comments(
    post_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminPostLockData]:
    locked = await service.set_comments_locked(
        principal,
        post_id,
        locked=False,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminPostLockData(post_id=post_id, comments_locked=locked),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.delete(
    "/posts/{post_id}",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminPostDeletionData],
    responses=PRIVATE_RESPONSES,
)
async def admin_delete_post(
    post_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminPostDeletionData]:
    deleted_at = await service.admin_delete_post(
        principal,
        post_id,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminPostDeletionData(
            post_id=post_id,
            is_deleted=True,
            deleted_at=deleted_at,
            restored_status=None,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/comments",
    response_model=PaginatedSuccessEnvelope[list[CommunityAdminCommentWorkspaceData]],
    responses=PRIVATE_RESPONSES,
)
async def list_admin_comments(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityAdminServiceDependency,
    query: Annotated[str | None, Query(alias="q", min_length=1, max_length=160)] = None,
    post_id: Annotated[UUID | None, Query(alias="postId")] = None,
    author_username: Annotated[
        str | None, Query(alias="authorUsername", min_length=1, max_length=64)
    ] = None,
    visibility: Annotated[
        Literal["VISIBLE", "HIDDEN", "DELETED", "ALL"], Query()
    ] = "ALL",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityAdminCommentWorkspaceData]]:
    result = await service.list_admin_comments(
        principal,
        query=query.strip() if query else None,
        post_id=post_id,
        author_username=author_username,
        visibility=visibility,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_admin_comment_data(row) for row in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@admin_router.post(
    "/comments/{comment_id}/delete",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminCommentStateData],
    responses=PRIVATE_RESPONSES,
)
async def admin_delete_comment(
    comment_id: UUID,
    payload: CommunityActionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminCommentStateData]:
    visibility = await service.admin_delete_comment(
        principal,
        comment_id,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminCommentStateData(
            comment_id=comment_id,
            visibility=cast(Literal["VISIBLE", "HIDDEN", "DELETED"], visibility),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/members",
    response_model=PaginatedSuccessEnvelope[list[CommunityAdminMemberWorkspaceData]],
    responses=PRIVATE_RESPONSES,
)
async def list_admin_members(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityAdminServiceDependency,
    query: Annotated[str | None, Query(alias="q", min_length=1, max_length=160)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityAdminMemberWorkspaceData]]:
    result = await service.list_admin_members(
        principal,
        query=query.strip() if query else None,
        page=page,
        page_size=page_size,
    )
    data = [
        CommunityAdminMemberWorkspaceData(
            member=_admin_member_card(
                row.user.id,
                row.profile.username if row.profile else None,
                row.profile.display_name if row.profile else None,
                row.profile.avatar_url if row.profile else None,
            ),
            published_post_count=row.published_post_count,
            comment_count=row.comment_count,
            follower_count=row.follower_count,
            following_count=row.following_count,
            last_activity_at=row.last_activity_at,
            active_restrictions=[
                CommunityAdminActiveRestriction(
                    id=restriction.id,
                    scope=cast(Literal["POSTS", "COMMENTS"], restriction.scope),
                    expires_at=_as_utc(restriction.expires_at),
                )
                for restriction in row.active_restrictions
            ],
        )
        for row in result.items
    ]
    return PaginatedSuccessEnvelope(
        data=data,
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@admin_router.post(
    "/members/{member_id}/restrictions",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CommunityMemberRestrictionData],
    responses=PRIVATE_RESPONSES,
)
async def create_member_restriction(
    member_id: UUID,
    payload: CommunityMemberRestrictionCreateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityMemberRestrictionData]:
    row = await service.create_member_restriction(
        principal,
        member_id,
        payload,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=_restriction_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/members/{member_id}/restrictions",
    response_model=PaginatedSuccessEnvelope[list[CommunityMemberRestrictionData]],
    responses=PRIVATE_RESPONSES,
)
async def list_member_restrictions(
    member_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityAdminServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityMemberRestrictionData]]:
    result = await service.list_member_restrictions(
        principal,
        member_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_restriction_data(item) for item in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@admin_router.delete(
    "/members/{member_id}/restrictions/{restriction_id}",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityMemberRestrictionData],
    responses=PRIVATE_RESPONSES,
)
async def revoke_member_restriction(
    member_id: UUID,
    restriction_id: UUID,
    payload: CommunityMemberRestrictionRevokeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityMemberRestrictionData]:
    row = await service.revoke_member_restriction(
        principal,
        member_id,
        restriction_id,
        payload,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=_restriction_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/categories",
    response_model=SuccessEnvelope[list[CommunityAdminCategoryData]],
    responses=PRIVATE_RESPONSES,
)
async def list_categories(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[list[CommunityAdminCategoryData]]:
    categories = await service.list_categories(principal)
    return SuccessEnvelope(
        data=[CommunityAdminCategoryData.model_validate(item) for item in categories],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.post(
    "/categories",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CommunityAdminCategoryData],
    responses=PRIVATE_RESPONSES,
)
async def create_category(
    payload: CommunityCategoryCreateRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminCategoryData]:
    category = await service.create_category(
        principal,
        payload,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminCategoryData.model_validate(category),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.patch(
    "/categories/{category_id}",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminCategoryData],
    responses=PRIVATE_RESPONSES,
)
async def update_category(
    category_id: UUID,
    payload: CommunityCategoryPatchRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminCategoryData]:
    category = await service.update_category(
        principal,
        category_id,
        payload,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminCategoryData.model_validate(category),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/settings",
    response_model=SuccessEnvelope[CommunityAdminSettingsData],
    responses=PRIVATE_RESPONSES,
)
async def get_settings(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminSettingsData]:
    settings = await service.get_settings(principal)
    return SuccessEnvelope(
        data=CommunityAdminSettingsData(
            pre_moderation_enabled=settings.pre_moderation_enabled,
            updated_at=settings.updated_at,
            updated_by=settings.updated_by_user_id,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.put(
    "/settings",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityAdminSettingsData],
    responses=PRIVATE_RESPONSES,
)
async def update_settings(
    payload: CommunitySettingsRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityAdminServiceDependency,
) -> SuccessEnvelope[CommunityAdminSettingsData]:
    settings = await service.update_settings(
        principal,
        payload,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CommunityAdminSettingsData(
            pre_moderation_enabled=settings.pre_moderation_enabled,
            updated_at=settings.updated_at,
            updated_by=settings.updated_by_user_id,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@admin_router.get(
    "/moderation-history",
    response_model=PaginatedSuccessEnvelope[list[CommunityModerationEventData]],
    responses=PRIVATE_RESPONSES,
)
async def list_moderation_history(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityAdminServiceDependency,
    target_type: Annotated[
        Literal["POST", "COMMENT", "MEMBER", "CATEGORY", "SETTINGS"] | None,
        Query(alias="targetType"),
    ] = None,
    target_id: Annotated[
        str | None,
        Query(alias="targetId", min_length=1, max_length=64),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityModerationEventData]]:
    result = await service.list_moderation_events(
        principal,
        target_type=target_type,
        target_id=target_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_event_data(row) for row in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )
