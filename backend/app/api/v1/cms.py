from uuid import UUID

from fastapi import APIRouter, Query, Request, status

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
from app.modules.cms.dependencies import CmsServiceDependency
from app.modules.cms.models import CmsContentStatus
from app.modules.cms.schemas import (
    CmsBannerData,
    CmsBannerRequest,
    CmsCategoryData,
    CmsCategoryRequest,
    CmsPageData,
    CmsPageRequest,
    CmsPostData,
    CmsPostRequest,
    CmsStatusRequest,
)
from app.modules.cms.service import (
    CmsBannerInput,
    CmsCategoryInput,
    CmsPageInput,
    CmsPostInput,
)

router = APIRouter(prefix="/api/v1", tags=["cms"])


@router.get(
    "/admin/cms/posts", response_model=PaginatedSuccessEnvelope[list[CmsPostData]]
)
async def admin_posts(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CmsServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[CmsPostData]]:
    rows, total = await service.list_posts(principal, page=page, page_size=page_size)
    return PaginatedSuccessEnvelope(
        data=[CmsPostData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/admin/cms/posts",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CmsPostData],
)
async def create_post(
    payload: CmsPostRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPostData]:
    row = await service.create_post(
        principal,
        CmsPostInput(
            payload.title,
            payload.slug,
            payload.excerpt,
            payload.body_html,
            payload.category_id,
        ),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsPostData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put("/admin/cms/posts/{post_id}", response_model=SuccessEnvelope[CmsPostData])
async def update_post(
    post_id: UUID,
    payload: CmsPostRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPostData]:
    row = await service.update_post(
        principal,
        post_id,
        CmsPostInput(
            payload.title,
            payload.slug,
            payload.excerpt,
            payload.body_html,
            payload.category_id,
        ),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsPostData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/admin/cms/posts/{post_id}/status", response_model=SuccessEnvelope[CmsPostData]
)
async def set_post_status(
    post_id: UUID,
    payload: CmsStatusRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPostData]:
    row = await service.set_post_status(
        principal, post_id, payload.status, request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=CmsPostData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/admin/cms/posts/{post_id}", response_model=SuccessEnvelope[CmsPostData]
)
async def archive_post(
    post_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPostData]:
    row = await service.set_post_status(
        principal,
        post_id,
        CmsContentStatus.ARCHIVED,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsPostData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/cms/posts/{post_id}/publish", response_model=SuccessEnvelope[CmsPostData]
)
async def publish_post(
    post_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPostData]:
    row = await service.publish_post(
        principal, post_id, request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=CmsPostData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/public/posts", response_model=PaginatedSuccessEnvelope[list[CmsPostData]])
async def public_posts(
    request: Request,
    service: CmsServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[CmsPostData]]:
    rows, total = await service.list_public_posts(page=page, page_size=page_size)
    return PaginatedSuccessEnvelope(
        data=[CmsPostData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get("/public/posts/{slug}", response_model=SuccessEnvelope[CmsPostData])
async def public_post(
    slug: str, request: Request, service: CmsServiceDependency
) -> SuccessEnvelope[CmsPostData]:
    row = await service.get_public_post(slug)
    return SuccessEnvelope(
        data=CmsPostData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/admin/cms/pages", response_model=SuccessEnvelope[list[CmsPageData]])
async def admin_pages(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[list[CmsPageData]]:
    rows = await service.list_pages(principal)
    return SuccessEnvelope(
        data=[CmsPageData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/cms/pages", status_code=201, response_model=SuccessEnvelope[CmsPageData]
)
async def create_page(
    payload: CmsPageRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPageData]:
    row = await service.create_page(
        principal,
        CmsPageInput(payload.title, payload.slug, payload.body_html),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsPageData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put("/admin/cms/pages/{item_id}", response_model=SuccessEnvelope[CmsPageData])
async def update_page(
    item_id: UUID,
    payload: CmsPageRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPageData]:
    row = await service.update_page(
        principal,
        item_id,
        CmsPageInput(payload.title, payload.slug, payload.body_html),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsPageData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/cms/pages/{item_id}/publish", response_model=SuccessEnvelope[CmsPageData]
)
async def publish_page(
    item_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPageData]:
    row = await service.publish_page(
        principal, item_id, request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=CmsPageData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/admin/cms/pages/{item_id}", response_model=SuccessEnvelope[CmsPageData]
)
async def archive_page(
    item_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsPageData]:
    row = await service.archive_page(
        principal, item_id, request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=CmsPageData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/admin/cms/banners", response_model=SuccessEnvelope[list[CmsBannerData]])
async def admin_banners(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[list[CmsBannerData]]:
    rows = await service.list_banners(principal)
    return SuccessEnvelope(
        data=[CmsBannerData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/cms/banners", status_code=201, response_model=SuccessEnvelope[CmsBannerData]
)
async def create_banner(
    payload: CmsBannerRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsBannerData]:
    row = await service.create_banner(
        principal,
        CmsBannerInput(
            payload.title, payload.slug, payload.image_url, payload.link_url
        ),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsBannerData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/admin/cms/banners/{item_id}", response_model=SuccessEnvelope[CmsBannerData]
)
async def update_banner(
    item_id: UUID,
    payload: CmsBannerRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsBannerData]:
    row = await service.update_banner(
        principal,
        item_id,
        CmsBannerInput(
            payload.title, payload.slug, payload.image_url, payload.link_url
        ),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsBannerData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/cms/banners/{item_id}/publish",
    response_model=SuccessEnvelope[CmsBannerData],
)
async def publish_banner(
    item_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsBannerData]:
    row = await service.publish_banner(
        principal, item_id, request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=CmsBannerData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/admin/cms/banners/{item_id}", response_model=SuccessEnvelope[CmsBannerData]
)
async def archive_banner(
    item_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsBannerData]:
    row = await service.archive_banner(
        principal, item_id, request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=CmsBannerData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/cms/categories", response_model=SuccessEnvelope[list[CmsCategoryData]]
)
async def admin_categories(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[list[CmsCategoryData]]:
    rows = await service.list_categories(principal)
    return SuccessEnvelope(
        data=[CmsCategoryData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/cms/categories",
    status_code=201,
    response_model=SuccessEnvelope[CmsCategoryData],
)
async def create_category(
    payload: CmsCategoryRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsCategoryData]:
    row = await service.create_category(
        principal,
        CmsCategoryInput(payload.name, payload.slug, payload.description),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsCategoryData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/admin/cms/categories/{item_id}", response_model=SuccessEnvelope[CmsCategoryData]
)
async def update_category(
    item_id: UUID,
    payload: CmsCategoryRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsCategoryData]:
    row = await service.update_category(
        principal,
        item_id,
        CmsCategoryInput(payload.name, payload.slug, payload.description),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsCategoryData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/admin/cms/categories/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_category(
    item_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> None:
    await service.delete_category(
        principal, item_id, request_id=request.state.request_id
    )
