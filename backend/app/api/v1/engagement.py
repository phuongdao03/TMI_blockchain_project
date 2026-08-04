from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response, status

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
from app.modules.engagement.dependencies import (
    ActivityServiceDependency,
    FavoriteServiceDependency,
)
from app.modules.engagement.schemas import ActivityData, ActivityPageData, FavoriteData
from app.modules.public.publication_dependencies import PublicQrCodeServiceDependency

router = APIRouter(prefix="/api/v1", tags=["engagement"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "CSRF validation failed.", "model": ErrorEnvelope},
    404: {"description": "Public work was not found.", "model": ErrorEnvelope},
    422: {"description": "Request validation failed.", "model": ErrorEnvelope},
}
FavoriteSlugPath = Annotated[str, Path(min_length=1, max_length=180)]


@router.put(
    "/public/works/{slug}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        401: PRIVATE_RESPONSES[401],
        403: PRIVATE_RESPONSES[403],
        404: PRIVATE_RESPONSES[404],
    },
)
async def add_favorite(
    slug: FavoriteSlugPath,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: FavoriteServiceDependency,
) -> Response:
    await service.add(
        principal,
        slug=slug,
        request_id=request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/public/works/{slug}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        401: PRIVATE_RESPONSES[401],
        403: PRIVATE_RESPONSES[403],
        404: PRIVATE_RESPONSES[404],
    },
)
async def remove_favorite(
    slug: FavoriteSlugPath,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: FavoriteServiceDependency,
) -> Response:
    await service.remove(
        principal,
        slug=slug,
        request_id=request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me/favorites",
    response_model=PaginatedSuccessEnvelope[list[FavoriteData]],
    responses={401: PRIVATE_RESPONSES[401], 422: PRIVATE_RESPONSES[422]},
)
async def list_favorites(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: FavoriteServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[FavoriteData]]:
    rows, total = await service.list_for_user(
        principal,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[FavoriteData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/me/activity",
    response_model=SuccessEnvelope[ActivityPageData],
    responses={401: PRIVATE_RESPONSES[401], 422: PRIVATE_RESPONSES[422]},
)
async def list_activity(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ActivityServiceDependency,
    cursor: Annotated[str | None, Query(min_length=1, max_length=512)] = None,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
) -> SuccessEnvelope[ActivityPageData]:
    rows, next_cursor = await service.list_for_user(
        principal,
        cursor=cursor,
        limit=page_size,
    )
    return SuccessEnvelope(
        data=ActivityPageData(
            items=[ActivityData.model_validate(row) for row in rows],
            next_cursor=next_cursor,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
@router.delete(
    "/admin/public/works/{work_id}/share-link",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        401: PRIVATE_RESPONSES[401],
        403: PRIVATE_RESPONSES[403],
    },
)
async def revoke_public_share_link(
    work_id: UUID,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicQrCodeServiceDependency,
) -> Response:
    await service.revoke(principal, public_work_id=work_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
