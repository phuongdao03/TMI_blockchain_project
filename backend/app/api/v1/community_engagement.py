from datetime import datetime
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
    OptionalCurrentPrincipalDependency,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.dependencies import CommunityEngagementServiceDependency
from app.modules.community.engagement_repository import (
    CommunityCommentRow,
    CommunityCommentThread,
    CommunityMemberDirectoryRecord,
    CommunityMemberListRecord,
)
from app.modules.community.engagement_schemas import (
    CommunityBookmarkStateData,
    CommunityCommentData,
    CommunityCommentEditRequest,
    CommunityCommentLikeStateData,
    CommunityCommentReplyData,
    CommunityCommentRequest,
    CommunityCommentThreadData,
    CommunityFollowStateData,
    CommunityLikeStateData,
    CommunityMemberData,
    CommunityMemberDirectoryItemData,
    CommunityMemberDirectoryPageData,
    CommunityMemberListItemData,
    CommunityMemberProfileEditRequest,
)
from app.modules.community.engagement_service import (
    CommunityEngagementService,
    CommunityMemberView,
)
from app.modules.community.identity import public_user_identity
from app.modules.community.rate_limit import (
    enforce_community_content_write_rate_limit,
    enforce_community_engagement_write_rate_limit,
)
from app.modules.community.repository import CommunityPostRow
from app.modules.community.schemas import (
    CommunityAuthorData,
    CommunityCategoryData,
    CommunityPostData,
    CommunityRelatedWorkData,
    CommunityTagData,
)
from app.modules.community.service import CommunityPostPage
from app.modules.engagement.visitor import get_or_issue_engagement_visitor
from app.modules.public.dependencies import enforce_public_engagement_rate_limit

router = APIRouter(prefix="/api/v1/community", tags=["community-engagement"])
_DELETED_COMMENT_CONTENT = "Bình luận đã bị xóa."
_HIDDEN_COMMENT_CONTENT = "Bình luận đã bị ẩn."

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Community action is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Community content was not found.", "model": ErrorEnvelope},
    409: {"description": "Community state conflict.", "model": ErrorEnvelope},
    422: {"description": "Community request is invalid.", "model": ErrorEnvelope},
}


def _author(
    username: str | None,
    display_name: str | None,
    avatar_url: str | None,
    avatar_media_id: UUID | None,
    user_id: UUID,
    *,
    is_admin: bool,
    is_moderator: bool,
    membership_tier: str = "MEMBER",
) -> CommunityAuthorData:
    identity = public_user_identity(
        display_name=display_name,
        avatar_url=avatar_url,
        avatar_media_id=avatar_media_id,
        is_admin=is_admin,
        is_moderator=is_moderator,
    )
    return CommunityAuthorData(
        id=user_id,
        username=username or f"member-{user_id.hex}",
        display_name=identity.display_name,
        avatar_url=identity.avatar_url,
        role_label=identity.role_label,
        is_admin=identity.is_admin,
        membership_tier=cast(
            Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"], membership_tier
        ),
    )


def _post_data(row: CommunityPostRow) -> CommunityPostData:
    return CommunityPostData(
        id=row.post.id,
        slug=row.post.slug,
        title=row.post.title,
        excerpt=row.post.excerpt,
        category=CommunityCategoryData.model_validate(row.category),
        author=_author(
            row.author_username,
            row.author_display_name,
            row.author_avatar_url,
            row.author_avatar_media_id,
            row.post.author_user_id,
            is_admin=row.author_is_admin,
            is_moderator=row.author_is_moderator,
            membership_tier=row.author_membership_tier,
        ),
        published_at=cast(datetime, row.post.published_at),
        view_count=row.post.view_count,
        is_pinned=row.post.pinned_at is not None,
        like_count=row.like_count,
        comment_count=row.comment_count,
        viewer_has_liked=row.viewer_has_liked,
        viewer_has_bookmarked=row.viewer_has_bookmarked,
        related_work=(
            CommunityRelatedWorkData(
                id=row.related_work_id,
                title=row.related_work_title,
                slug=row.related_work_slug,
            )
            if (
                row.related_work_id is not None
                and row.related_work_title is not None
                and row.related_work_slug is not None
            )
            else None
        ),
        tags=[CommunityTagData.model_validate(tag) for tag in row.tags],
    )


def _comment_author(row: CommunityCommentRow) -> CommunityAuthorData:
    return _author(
        row.author_username,
        row.author_display_name,
        row.author_avatar_url,
        row.author_avatar_media_id,
        row.comment.author_user_id,
        is_admin=row.author_is_admin,
        is_moderator=row.author_is_moderator,
        membership_tier=row.author_membership_tier,
    )


def _comment_data(row: CommunityCommentRow) -> CommunityCommentData:
    deleted = row.comment.deleted_at is not None
    hidden = row.comment.moderation_hidden_at is not None
    tombstone = deleted or hidden
    return CommunityCommentData(
        id=row.comment.id,
        post_id=row.comment.post_id,
        parent_id=row.comment.parent_id,
        content=(
            _DELETED_COMMENT_CONTENT
            if deleted
            else _HIDDEN_COMMENT_CONTENT
            if hidden
            else row.comment.content
        ),
        author=None if tombstone else _comment_author(row),
        is_deleted=tombstone,
        created_at=row.comment.created_at,
        like_count=0 if tombstone else row.like_count,
        viewer_has_liked=False if tombstone else row.viewer_has_liked,
    )


def _comment_thread_data(
    thread: CommunityCommentThread,
) -> CommunityCommentThreadData:
    root_deleted = thread.root.comment.deleted_at is not None
    root_hidden = thread.root.comment.moderation_hidden_at is not None
    root_tombstone = root_deleted or root_hidden
    return CommunityCommentThreadData(
        id=thread.root.comment.id,
        parent_id=None,
        content=(
            _DELETED_COMMENT_CONTENT
            if root_deleted
            else thread.root.comment.content
            if not root_hidden
            else _HIDDEN_COMMENT_CONTENT
        ),
        author=(None if root_tombstone else _comment_author(thread.root)),
        is_deleted=root_tombstone,
        created_at=thread.root.comment.created_at,
        like_count=0 if root_tombstone else thread.root.like_count,
        viewer_has_liked=(False if root_tombstone else thread.root.viewer_has_liked),
        replies=[
            CommunityCommentReplyData(
                id=reply.comment.id,
                parent_id=cast(UUID, reply.comment.parent_id),
                content=(
                    _DELETED_COMMENT_CONTENT
                    if reply.comment.deleted_at is not None
                    else reply.comment.content
                    if reply.comment.moderation_hidden_at is None
                    else _HIDDEN_COMMENT_CONTENT
                ),
                author=(
                    None
                    if (
                        reply.comment.deleted_at is not None
                        or reply.comment.moderation_hidden_at is not None
                    )
                    else _comment_author(reply)
                ),
                is_deleted=(
                    reply.comment.deleted_at is not None
                    or reply.comment.moderation_hidden_at is not None
                ),
                created_at=reply.comment.created_at,
                like_count=(
                    0
                    if (
                        reply.comment.deleted_at is not None
                        or reply.comment.moderation_hidden_at is not None
                    )
                    else reply.like_count
                ),
                viewer_has_liked=(
                    False
                    if (
                        reply.comment.deleted_at is not None
                        or reply.comment.moderation_hidden_at is not None
                    )
                    else reply.viewer_has_liked
                ),
            )
            for reply in thread.replies
        ],
    )


def _member_data(view: CommunityMemberView) -> CommunityMemberData:
    record = view.member
    profile = record.profile
    identity = public_user_identity(
        display_name=(
            record.public_profile.display_name
            if record.public_profile is not None
            else profile.display_name
        ),
        avatar_url=(
            record.public_profile.avatar_url
            if record.public_profile is not None
            else profile.avatar_url
        ),
        avatar_media_id=(
            record.public_profile.avatar_media_id
            if record.public_profile is not None
            else profile.avatar_media_id
        ),
        is_admin=record.is_admin,
        is_moderator=record.is_moderator,
    )
    return CommunityMemberData(
        id=record.user.id,
        username=profile.username,
        display_name=identity.display_name,
        avatar_url=identity.avatar_url,
        role_label=identity.role_label,
        is_admin=identity.is_admin,
        membership_tier=cast(
            Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"],
            record.membership_tier,
        ),
        bio=profile.bio,
        professional_title=profile.professional_title,
        organization=profile.organization,
        activity_fields=profile.activity_fields,
        professional_links=profile.professional_links,
        joined_at=record.user.created_at,
        published_post_count=view.published_post_count,
        follower_count=view.follower_count,
        following_count=view.following_count,
        viewer_is_following=view.viewer_is_following,
    )


def _member_directory_item(
    record: CommunityMemberDirectoryRecord,
) -> CommunityMemberDirectoryItemData:
    identity = public_user_identity(
        display_name=(
            record.public_profile.display_name
            if record.public_profile is not None
            else None
        ),
        avatar_url=(
            record.public_profile.avatar_url
            if record.public_profile is not None
            else None
        ),
        avatar_media_id=(
            record.public_profile.avatar_media_id
            if record.public_profile is not None
            else None
        ),
        is_admin=False,
        is_moderator=False,
    )
    return CommunityMemberDirectoryItemData(
        id=record.user.id,
        username=record.profile.username,
        display_name=identity.display_name,
        avatar_url=identity.avatar_url,
        membership_tier=cast(
            Literal["MEMBER", "SILVER", "COMPANION", "PRESTIGE"],
            record.membership_tier,
        ),
        professional_title=record.profile.professional_title,
        organization=record.profile.organization,
        activity_fields=record.profile.activity_fields,
        professional_links=record.profile.professional_links,
    )


def _member_list_item(
    record: CommunityMemberListRecord,
) -> CommunityMemberListItemData:
    identity = public_user_identity(
        display_name=(
            record.public_profile.display_name
            if record.public_profile is not None
            else record.profile.display_name
        ),
        avatar_url=(
            record.public_profile.avatar_url
            if record.public_profile is not None
            else record.profile.avatar_url
        ),
        avatar_media_id=(
            record.public_profile.avatar_media_id
            if record.public_profile is not None
            else record.profile.avatar_media_id
        ),
        is_admin=record.is_admin,
        is_moderator=record.is_moderator,
    )
    return CommunityMemberListItemData(
        id=record.user.id,
        username=record.profile.username,
        display_name=identity.display_name,
        avatar_url=identity.avatar_url,
        role_label=identity.role_label,
        is_admin=identity.is_admin,
        viewer_is_following=record.viewer_is_following,
    )


def _paginated_posts(
    request: Request,
    page: int,
    page_size: int,
    result: CommunityPostPage,
) -> PaginatedSuccessEnvelope[list[CommunityPostData]]:
    return PaginatedSuccessEnvelope(
        data=[_post_data(row) for row in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/posts/{post_id}/comments",
    response_model=PaginatedSuccessEnvelope[list[CommunityCommentThreadData]],
)
async def list_comments(
    post_id: UUID,
    request: Request,
    service: CommunityEngagementServiceDependency,
    principal: OptionalCurrentPrincipalDependency,
    sort: Literal["oldest", "newest"] = "oldest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityCommentThreadData]]:
    result = await service.list_comments(
        post_id,
        viewer_user_id=principal.user_id if principal is not None else None,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_comment_thread_data(thread) for thread in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.post(
    "/posts/{post_id}/views",
    dependencies=[Depends(enforce_public_engagement_rate_limit)],
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        404: {"description": "Community post was not found.", "model": ErrorEnvelope},
        429: {"description": "Engagement rate limited.", "model": ErrorEnvelope},
        503: {
            "description": "Engagement tracking unavailable.",
            "model": ErrorEnvelope,
        },
    },
)
async def record_post_view(
    post_id: UUID,
    request: Request,
    response: Response,
    service: CommunityEngagementServiceDependency,
) -> Response:
    await service.record_post_view(
        post_id,
        visitor=get_or_issue_engagement_visitor(request, response),
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/posts/{post_id}/comments",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CommunityCommentData],
    responses=PRIVATE_RESPONSES,
)
async def create_comment(
    post_id: UUID,
    payload: CommunityCommentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityCommentData]:
    row = await service.create_comment(principal, post_id, payload)
    return SuccessEnvelope(
        data=_comment_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/comments/{comment_id}",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityCommentData],
    responses=PRIVATE_RESPONSES,
)
async def update_comment(
    comment_id: UUID,
    payload: CommunityCommentEditRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityCommentData]:
    row = await service.update_comment(principal, comment_id, payload.content)
    return SuccessEnvelope(
        data=_comment_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/comments/{comment_id}",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    status_code=status.HTTP_204_NO_CONTENT,
    responses=PRIVATE_RESPONSES,
)
async def delete_comment(
    comment_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> None:
    await service.delete_comment(principal, comment_id)


@router.put(
    "/comments/{comment_id}/like",
    dependencies=[Depends(enforce_community_engagement_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityCommentLikeStateData],
    responses=PRIVATE_RESPONSES,
)
async def like_comment(
    comment_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityCommentLikeStateData]:
    count, liked = await service.set_comment_like(
        principal,
        comment_id,
        is_liked=True,
    )
    return SuccessEnvelope(
        data=CommunityCommentLikeStateData(
            comment_id=comment_id,
            like_count=count,
            is_liked=liked,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/comments/{comment_id}/like",
    dependencies=[Depends(enforce_community_engagement_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityCommentLikeStateData],
    responses=PRIVATE_RESPONSES,
)
async def unlike_comment(
    comment_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityCommentLikeStateData]:
    count, liked = await service.set_comment_like(
        principal,
        comment_id,
        is_liked=False,
    )
    return SuccessEnvelope(
        data=CommunityCommentLikeStateData(
            comment_id=comment_id,
            like_count=count,
            is_liked=liked,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/posts/{post_id}/like",
    dependencies=[Depends(enforce_community_engagement_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityLikeStateData],
    responses=PRIVATE_RESPONSES,
)
async def like_post(
    post_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityLikeStateData]:
    count, liked = await service.set_like(principal, post_id, is_liked=True)
    return SuccessEnvelope(
        data=CommunityLikeStateData(
            post_id=post_id,
            like_count=count,
            is_liked=liked,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/posts/{post_id}/like",
    dependencies=[Depends(enforce_community_engagement_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityLikeStateData],
    responses=PRIVATE_RESPONSES,
)
async def unlike_post(
    post_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityLikeStateData]:
    count, liked = await service.set_like(principal, post_id, is_liked=False)
    return SuccessEnvelope(
        data=CommunityLikeStateData(
            post_id=post_id,
            like_count=count,
            is_liked=liked,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/posts/{post_id}/bookmark",
    dependencies=[Depends(enforce_community_engagement_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityBookmarkStateData],
    responses=PRIVATE_RESPONSES,
)
async def bookmark_post(
    post_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityBookmarkStateData]:
    is_bookmarked = await service.set_bookmark(
        principal,
        post_id,
        is_bookmarked=True,
    )
    return SuccessEnvelope(
        data=CommunityBookmarkStateData(
            post_id=post_id,
            is_bookmarked=is_bookmarked,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/posts/{post_id}/bookmark",
    dependencies=[Depends(enforce_community_engagement_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityBookmarkStateData],
    responses=PRIVATE_RESPONSES,
)
async def unbookmark_post(
    post_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityBookmarkStateData]:
    is_bookmarked = await service.set_bookmark(
        principal,
        post_id,
        is_bookmarked=False,
    )
    return SuccessEnvelope(
        data=CommunityBookmarkStateData(
            post_id=post_id,
            is_bookmarked=is_bookmarked,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/members/me", response_model=SuccessEnvelope[CommunityMemberData])
async def own_member_profile(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityMemberData]:
    view = await service.member_profile(
        principal.user_id,
        viewer_user_id=principal.user_id,
    )
    return SuccessEnvelope(
        data=_member_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/members/me",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityMemberData],
    responses=PRIVATE_RESPONSES,
)
async def edit_own_member_profile(
    payload: CommunityMemberProfileEditRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityMemberData]:
    view = await service.update_member_profile(principal, payload)
    return SuccessEnvelope(
        data=_member_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/members/me/bookmarks",
    response_model=PaginatedSuccessEnvelope[list[CommunityPostData]],
    responses=PRIVATE_RESPONSES,
)
async def list_bookmarks(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityEngagementServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityPostData]]:
    result = await service.bookmarks(
        principal,
        page=page,
        page_size=page_size,
    )
    return _paginated_posts(request, page, page_size, result)


async def _member_relation_page(
    *,
    username: str,
    relation_kind: Literal["followers", "following"],
    request: Request,
    principal: AuthPrincipal | None,
    service: CommunityEngagementService,
    page: int,
    page_size: int,
) -> PaginatedSuccessEnvelope[list[CommunityMemberListItemData]]:
    items, total = await service.member_relations(
        username,
        relation_kind=relation_kind,
        viewer_user_id=principal.user_id if principal is not None else None,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_member_list_item(item) for item in items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/members/{username}/followers",
    response_model=PaginatedSuccessEnvelope[list[CommunityMemberListItemData]],
)
async def list_member_followers(
    username: str,
    request: Request,
    principal: OptionalCurrentPrincipalDependency,
    service: CommunityEngagementServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityMemberListItemData]]:
    return await _member_relation_page(
        username=username,
        relation_kind="followers",
        request=request,
        principal=principal,
        service=service,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/members/{username}/following",
    response_model=PaginatedSuccessEnvelope[list[CommunityMemberListItemData]],
)
async def list_member_following(
    username: str,
    request: Request,
    principal: OptionalCurrentPrincipalDependency,
    service: CommunityEngagementServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityMemberListItemData]]:
    return await _member_relation_page(
        username=username,
        relation_kind="following",
        request=request,
        principal=principal,
        service=service,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/members/{username}/posts",
    response_model=PaginatedSuccessEnvelope[list[CommunityPostData]],
)
async def list_member_posts(
    username: str,
    request: Request,
    principal: OptionalCurrentPrincipalDependency,
    service: CommunityEngagementServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> PaginatedSuccessEnvelope[list[CommunityPostData]]:
    result = await service.member_posts(
        username,
        viewer_user_id=principal.user_id if principal is not None else None,
        page=page,
        page_size=page_size,
    )
    return _paginated_posts(request, page, page_size, result)


@router.get(
    "/members/directory",
    response_model=SuccessEnvelope[CommunityMemberDirectoryPageData],
)
async def search_member_directory(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityEngagementServiceDependency,
    q: Annotated[str, Query(min_length=2, max_length=120)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> SuccessEnvelope[CommunityMemberDirectoryPageData]:
    members, total = await service.member_directory(
        principal, query=q, page=page, page_size=page_size
    )
    return SuccessEnvelope(
        data=CommunityMemberDirectoryPageData(
            members=[_member_directory_item(member) for member in members],
            total=total,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/members/{username}",
    response_model=SuccessEnvelope[CommunityMemberData],
)
async def get_member_profile(
    username: str,
    request: Request,
    principal: OptionalCurrentPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityMemberData]:
    view = await service.member_profile_by_username(
        username,
        viewer_user_id=principal.user_id if principal is not None else None,
    )
    return SuccessEnvelope(
        data=_member_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/members/{member_id}/follow",
    dependencies=[Depends(enforce_community_engagement_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityFollowStateData],
    responses=PRIVATE_RESPONSES,
)
async def follow_member(
    member_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityFollowStateData]:
    count = await service.set_follow(principal, member_id, is_following=True)
    return SuccessEnvelope(
        data=CommunityFollowStateData(
            member_id=member_id,
            is_following=True,
            follower_count=count,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/members/{member_id}/follow",
    dependencies=[Depends(enforce_community_engagement_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityFollowStateData],
    responses=PRIVATE_RESPONSES,
)
async def unfollow_member(
    member_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityEngagementServiceDependency,
) -> SuccessEnvelope[CommunityFollowStateData]:
    count = await service.set_follow(principal, member_id, is_following=False)
    return SuccessEnvelope(
        data=CommunityFollowStateData(
            member_id=member_id,
            is_following=False,
            follower_count=count,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
