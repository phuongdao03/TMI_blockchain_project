from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

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
    EmployeeProfileLinkDependency,
)
from app.modules.cms.dependencies import CmsServiceDependency
from app.modules.cms.models import CmsContentStatus
from app.modules.cms.schemas import (
    CmsBannerData,
    CmsBannerRequest,
    CmsCategoryData,
    CmsCategoryRequest,
    CmsGuideArticleData,
    CmsGuideArticleRequest,
    CmsGuideAudience,
    CmsGuideFeedbackAcceptedData,
    CmsGuideFeedbackData,
    CmsGuideFeedbackRequest,
    CmsPageData,
    CmsPageRequest,
    CmsPostData,
    CmsPostRequest,
    CmsStatusRequest,
)
from app.modules.cms.service import (
    CmsBannerInput,
    CmsCategoryInput,
    CmsGuideArticleInput,
    CmsPageInput,
    CmsPostInput,
)
from app.modules.public.dependencies import enforce_public_engagement_rate_limit

router = APIRouter(prefix="/api/v1", tags=["cms"])


def _guide_input(payload: CmsGuideArticleRequest) -> CmsGuideArticleInput:
    return CmsGuideArticleInput(
        title=payload.title,
        slug=payload.slug,
        summary=payload.summary,
        category=payload.category,
        audiences=tuple(audience.value for audience in payload.audiences),
        body_html=payload.body_html,
        sort_order=payload.sort_order,
    )


@router.get(
    "/public/guide/articles",
    response_model=PaginatedSuccessEnvelope[list[CmsGuideArticleData]],
)
async def public_guide_articles(
    request: Request,
    service: CmsServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    query: str | None = Query(default=None, alias="q", max_length=120),
    category: str | None = Query(default=None, max_length=80),
) -> PaginatedSuccessEnvelope[list[CmsGuideArticleData]]:
    rows, total = await service.list_public_guide_articles(
        page=page, page_size=page_size, query=query, category=category
    )
    return PaginatedSuccessEnvelope(
        data=[CmsGuideArticleData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/public/guide/articles/{slug}", response_model=SuccessEnvelope[CmsGuideArticleData]
)
async def public_guide_article(
    slug: str, request: Request, service: CmsServiceDependency
) -> SuccessEnvelope[CmsGuideArticleData]:
    row = await service.get_public_guide_article(slug)
    return SuccessEnvelope(
        data=CmsGuideArticleData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/public/guide/articles/{slug}/feedback",
    response_model=SuccessEnvelope[CmsGuideFeedbackAcceptedData],
    responses={
        429: {"description": "Engagement rate limited.", "model": ErrorEnvelope},
        503: {"description": "Engagement unavailable.", "model": ErrorEnvelope},
    },
    dependencies=[Depends(enforce_public_engagement_rate_limit)],
)
async def submit_guide_feedback(
    slug: str,
    payload: CmsGuideFeedbackRequest,
    request: Request,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsGuideFeedbackAcceptedData]:
    await service.record_guide_feedback(
        slug,
        helpful=payload.helpful,
        comment=payload.comment,
        client_token=str(payload.client_token),
    )
    return SuccessEnvelope(
        data=CmsGuideFeedbackAcceptedData(),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/guide/articles",
    response_model=PaginatedSuccessEnvelope[list[CmsGuideArticleData]],
)
async def accessible_guide_articles(
    request: Request,
    principal: CurrentPrincipalDependency,
    is_employee: EmployeeProfileLinkDependency,
    service: CmsServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    query: str | None = Query(default=None, alias="q", max_length=120),
    category: str | None = Query(default=None, max_length=80),
) -> PaginatedSuccessEnvelope[list[CmsGuideArticleData]]:
    rows, total = await service.list_accessible_guide_articles(
        principal,
        is_employee=is_employee,
        page=page,
        page_size=page_size,
        query=query,
        category=category,
    )
    return PaginatedSuccessEnvelope(
        data=[CmsGuideArticleData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/guide/articles/{slug}", response_model=SuccessEnvelope[CmsGuideArticleData]
)
async def accessible_guide_article(
    slug: str,
    request: Request,
    principal: CurrentPrincipalDependency,
    is_employee: EmployeeProfileLinkDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsGuideArticleData]:
    row = await service.get_accessible_guide_article(
        principal, slug, is_employee=is_employee
    )
    return SuccessEnvelope(
        data=CmsGuideArticleData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/cms/guide-articles",
    response_model=PaginatedSuccessEnvelope[list[CmsGuideArticleData]],
)
async def admin_guide_articles(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CmsServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    status_filter: CmsContentStatus | None = Query(default=None, alias="status"),  # noqa: B008
    audience: CmsGuideAudience | None = None,
    category: str | None = Query(default=None, max_length=80),
    query: str | None = Query(default=None, alias="q", max_length=120),
) -> PaginatedSuccessEnvelope[list[CmsGuideArticleData]]:
    rows, total = await service.list_admin_guide_articles(
        principal,
        page=page,
        page_size=page_size,
        status=status_filter,
        audience=audience.value if audience else None,
        category=category,
        query=query,
    )
    return PaginatedSuccessEnvelope(
        data=[CmsGuideArticleData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/admin/cms/guide-articles/{article_id}/feedback",
    response_model=PaginatedSuccessEnvelope[list[CmsGuideFeedbackData]],
)
async def admin_guide_feedback(
    article_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CmsServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[CmsGuideFeedbackData]]:
    rows, total = await service.list_admin_guide_feedback(
        principal, article_id, page=page, page_size=page_size
    )
    return PaginatedSuccessEnvelope(
        data=[CmsGuideFeedbackData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/admin/cms/guide-articles",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[CmsGuideArticleData],
)
async def create_guide_article(
    payload: CmsGuideArticleRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsGuideArticleData]:
    row = await service.create_guide_article(
        principal, _guide_input(payload), request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=CmsGuideArticleData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/admin/cms/guide-articles/{article_id}",
    response_model=SuccessEnvelope[CmsGuideArticleData],
)
async def update_guide_article(
    article_id: UUID,
    payload: CmsGuideArticleRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsGuideArticleData]:
    row = await service.update_guide_article(
        principal,
        article_id,
        _guide_input(payload),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CmsGuideArticleData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/admin/cms/guide-articles/{article_id}/status",
    response_model=SuccessEnvelope[CmsGuideArticleData],
)
async def set_guide_article_status(
    article_id: UUID,
    payload: CmsStatusRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[CmsGuideArticleData]:
    row = await service.set_guide_article_status(
        principal, article_id, payload.status, request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=CmsGuideArticleData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/admin/cms/guide-articles/{article_id}",
    response_model=SuccessEnvelope[bool],
)
async def delete_guide_article(
    article_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CmsServiceDependency,
) -> SuccessEnvelope[bool]:
    await service.delete_guide_article(
        principal, article_id, request_id=request.state.request_id
    )
    return SuccessEnvelope(
        data=True,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


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
