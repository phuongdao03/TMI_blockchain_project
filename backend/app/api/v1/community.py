from datetime import datetime
from typing import Annotated, Any, Literal, cast
from urllib.parse import quote
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
from app.modules.community.admin_schemas import CommunityAdminPostWorkspaceData
from app.modules.community.dependencies import (
    CommunityAdminServiceDependency,
    CommunityMediaDeliveryServiceDependency,
    CommunityServiceDependency,
)
from app.modules.community.errors import CommunityNotFoundError
from app.modules.community.models import CommunityPostStatus
from app.modules.community.rate_limit import enforce_community_content_write_rate_limit
from app.modules.community.repository import CommunityPostRow
from app.modules.community.schemas import (
    CommunityAuthorData,
    CommunityCategoryData,
    CommunityPostData,
    CommunityPostDetailData,
    CommunityPostImageData,
    CommunityPostRequest,
    CommunityPostWriteData,
    CommunityRelatedWorkData,
    CommunityTagData,
)
from app.modules.media.models import MediaConfidentiality, MediaStatus
from app.modules.media.types import (
    COMMUNITY_POST_IMAGE_MAX_BYTES,
    COMMUNITY_POST_IMAGE_MIME_TYPES,
    MediaPurpose,
)

router = APIRouter(prefix="/api/v1/community", tags=["community"])
moderation_router = APIRouter(
    prefix="/api/v1/admin/community",
    tags=["community-moderation"],
)

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Community access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Community content was not found.", "model": ErrorEnvelope},
    409: {"description": "Community state conflict.", "model": ErrorEnvelope},
    422: {"description": "Community request is invalid.", "model": ErrorEnvelope},
}


def _author(row: CommunityPostRow) -> CommunityAuthorData:
    return CommunityAuthorData(
        id=row.post.author_user_id,
        username=row.author_username or f"member-{row.post.author_user_id.hex}",
        display_name=row.author_display_name or "Th\u00e0nh vi\u00ean",
        avatar_url=row.author_avatar_url,
    )


def _category(row: CommunityPostRow) -> CommunityCategoryData:
    return CommunityCategoryData.model_validate(row.category)


def _related_work(row: CommunityPostRow) -> CommunityRelatedWorkData | None:
    if (
        row.related_work_id is None
        or row.related_work_title is None
        or row.related_work_slug is None
    ):
        return None
    return CommunityRelatedWorkData(
        id=row.related_work_id,
        title=row.related_work_title,
        slug=row.related_work_slug,
    )


def _images(row: CommunityPostRow) -> list[CommunityPostImageData]:
    images: list[CommunityPostImageData] = []
    for relation in row.post.image_relations:
        asset = relation.media_asset
        if (
            asset.purpose != MediaPurpose.COMMUNITY_POST.value
            or asset.status is not MediaStatus.ACTIVE
            or asset.deleted_at is not None
            or asset.inspected_at is None
            or asset.mime_type not in COMMUNITY_POST_IMAGE_MIME_TYPES
            or not 0 < asset.bytes <= COMMUNITY_POST_IMAGE_MAX_BYTES
            or asset.sha256 is None
            or asset.access_mode != "authenticated"
            or asset.confidentiality is not MediaConfidentiality.PRIVATE
        ):
            continue
        images.append(
            CommunityPostImageData(
                id=asset.id,
                url=(
                    f"/api/v1/community/posts/{quote(row.post.slug, safe='')}"
                    f"/media/{asset.id}"
                ),
            )
        )
    return images


def _tags(row: CommunityPostRow) -> list[CommunityTagData]:
    return [CommunityTagData.model_validate(tag) for tag in row.tags]


def _write_data(row: CommunityPostRow) -> CommunityPostWriteData:
    return CommunityPostWriteData(
        id=row.post.id,
        slug=row.post.slug,
        title=row.post.title,
        content=row.post.content,
        status=row.post.status,
        moderation_reason=row.post.moderation_reason,
        view_count=row.post.view_count,
        category=_category(row),
        related_work=_related_work(row),
        created_at=row.post.created_at,
        updated_at=row.post.updated_at,
        images=_images(row),
        tags=_tags(row),
    )


def _public_data(row: CommunityPostRow) -> CommunityPostData:
    return CommunityPostData(
        id=row.post.id,
        slug=row.post.slug,
        title=row.post.title,
        excerpt=row.post.excerpt,
        category=_category(row),
        author=_author(row),
        published_at=cast(datetime, row.post.published_at),
        view_count=row.post.view_count,
        is_pinned=row.post.pinned_at is not None,
        like_count=row.like_count,
        comment_count=row.comment_count,
        viewer_has_liked=row.viewer_has_liked,
        viewer_has_bookmarked=row.viewer_has_bookmarked,
        related_work=_related_work(row),
        images=_images(row),
        tags=_tags(row),
    )


def _admin_post_data(row: CommunityPostRow) -> CommunityAdminPostWorkspaceData:
    return CommunityAdminPostWorkspaceData(
        id=row.post.id,
        slug=row.post.slug,
        title=row.post.title,
        excerpt=row.post.excerpt,
        content=row.post.content,
        category=_category(row),
        author=_author(row),
        published_at=row.post.published_at,
        status=row.post.status.value,
        view_count=row.post.view_count,
        is_pinned=row.post.pinned_at is not None,
        like_count=row.like_count,
        comment_count=row.comment_count,
        viewer_has_liked=row.viewer_has_liked,
        viewer_has_bookmarked=row.viewer_has_bookmarked,
        related_work=_related_work(row),
        images=_images(row),
        tags=_tags(row),
        comments_locked=row.post.comments_locked_at is not None,
        deleted_at=row.post.deleted_at,
        pre_delete_status=row.post.pre_delete_status,
    )


@router.get(
    "/categories",
    response_model=SuccessEnvelope[list[CommunityCategoryData]],
)
async def list_categories(
    request: Request,
    service: CommunityServiceDependency,
) -> SuccessEnvelope[list[CommunityCategoryData]]:
    categories = await service.list_categories()
    return SuccessEnvelope(
        data=[
            CommunityCategoryData.model_validate(category) for category in categories
        ],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/posts",
    response_model=PaginatedSuccessEnvelope[list[CommunityPostData]],
)
async def list_posts(
    request: Request,
    service: CommunityServiceDependency,
    principal: OptionalCurrentPrincipalDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
    category: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    tag: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    related_work_id: Annotated[UUID | None, Query(alias="relatedWorkId")] = None,
    query: Annotated[
        str | None,
        Query(alias="q", min_length=1, max_length=120, pattern=r".*\S.*"),
    ] = None,
    sort: Literal["recent", "popular", "discussed", "following"] = "recent",
) -> PaginatedSuccessEnvelope[list[CommunityPostData]]:
    result = await service.list_public_posts(
        category_slug=category,
        tag_slug=tag,
        related_work_id=related_work_id,
        query=query,
        sort=sort,
        page=page,
        page_size=page_size,
        viewer_user_id=principal.user_id if principal is not None else None,
    )
    return PaginatedSuccessEnvelope(
        data=[_public_data(row) for row in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/members/me/posts",
    response_model=PaginatedSuccessEnvelope[list[CommunityPostWriteData]],
    responses=PRIVATE_RESPONSES,
)
async def list_my_posts(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
    post_status: Annotated[
        Literal["DRAFT", "PENDING", "PUBLISHED", "REJECTED", "HIDDEN"] | None,
        Query(alias="status"),
    ] = None,
) -> PaginatedSuccessEnvelope[list[CommunityPostWriteData]]:
    result = await service.list_owned_posts(
        principal,
        status=CommunityPostStatus(post_status) if post_status is not None else None,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_write_data(row) for row in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )


@router.get(
    "/members/me/posts/{post_id}",
    response_model=SuccessEnvelope[CommunityPostWriteData],
    responses=PRIVATE_RESPONSES,
)
async def get_my_post(
    post_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityServiceDependency,
) -> SuccessEnvelope[CommunityPostWriteData]:
    row = await service.get_owned_post(principal, post_id)
    return SuccessEnvelope(
        data=_write_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/avatars/{media_id}",
    responses={404: {"description": "Community avatar was not found."}},
)
async def get_community_avatar(
    media_id: UUID,
    service: CommunityMediaDeliveryServiceDependency,
) -> Response:
    image = await service.deliver_avatar(media_id)
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }.get(image.mime_type)
    if extension is None:
        raise CommunityNotFoundError()
    return Response(
        content=image.content,
        media_type=image.mime_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'inline; filename="community-avatar.{extension}"',
            "Content-Length": str(len(image.content)),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/posts/{slug}/media/{media_id}",
    responses=PRIVATE_RESPONSES,
)
async def get_community_post_image(
    slug: str,
    media_id: UUID,
    principal: OptionalCurrentPrincipalDependency,
    service: CommunityMediaDeliveryServiceDependency,
) -> Response:
    image = await service.deliver(
        slug=slug,
        media_id=media_id,
        viewer_user_id=principal.user_id if principal is not None else None,
    )
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }.get(image.mime_type)
    if extension is None:
        raise CommunityNotFoundError()
    return Response(
        content=image.content,
        media_type=image.mime_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'inline; filename="community-image.{extension}"',
            "Content-Length": str(len(image.content)),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/posts/{slug}",
    response_model=SuccessEnvelope[CommunityPostDetailData],
    responses={
        404: {
            "description": "Community post was not found.",
            "model": ErrorEnvelope,
        }
    },
)
async def get_post(
    slug: str,
    request: Request,
    service: CommunityServiceDependency,
    principal: OptionalCurrentPrincipalDependency,
) -> SuccessEnvelope[CommunityPostDetailData]:
    row = await service.get_public_post(
        slug,
        viewer_user_id=principal.user_id if principal is not None else None,
    )
    return SuccessEnvelope(
        data=CommunityPostDetailData(
            **_public_data(row).model_dump(),
            content=row.post.content,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/posts",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CommunityPostWriteData],
    responses=PRIVATE_RESPONSES,
)
async def create_draft(
    payload: CommunityPostRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityServiceDependency,
) -> SuccessEnvelope[CommunityPostWriteData]:
    row = await service.create_draft(principal, payload)
    return SuccessEnvelope(
        data=_write_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/posts/{post_id}/submit",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityPostWriteData],
    responses=PRIVATE_RESPONSES,
)
async def submit_post(
    post_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityServiceDependency,
) -> SuccessEnvelope[CommunityPostWriteData]:
    row = await service.submit(
        principal,
        post_id,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=_write_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/posts/{post_id}",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    response_model=SuccessEnvelope[CommunityPostWriteData],
    responses=PRIVATE_RESPONSES,
)
async def update_post(
    post_id: UUID,
    payload: CommunityPostRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityServiceDependency,
) -> SuccessEnvelope[CommunityPostWriteData]:
    row = await service.update_post(principal, post_id, payload)
    return SuccessEnvelope(
        data=_write_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/posts/{post_id}",
    dependencies=[Depends(enforce_community_content_write_rate_limit)],
    status_code=status.HTTP_204_NO_CONTENT,
    responses=PRIVATE_RESPONSES,
)
async def delete_post(
    post_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CommunityServiceDependency,
) -> Response:
    await service.delete_post(
        principal,
        post_id,
        request_id=request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@moderation_router.get(
    "/posts",
    response_model=PaginatedSuccessEnvelope[list[CommunityAdminPostWorkspaceData]],
    responses=PRIVATE_RESPONSES,
)
async def moderation_queue(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CommunityAdminServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
    post_status: Annotated[CommunityPostStatus | None, Query(alias="status")] = None,
    query: Annotated[str | None, Query(alias="q", min_length=1, max_length=160)] = None,
) -> PaginatedSuccessEnvelope[list[CommunityAdminPostWorkspaceData]]:
    result = await service.list_admin_posts(
        principal,
        query=query.strip() if query else None,
        status=post_status.value if post_status is not None else None,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[_admin_post_data(row) for row in result.items],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
        ),
    )
