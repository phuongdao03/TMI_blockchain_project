from typing import Annotated
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
from app.modules.public.editor_service import (
    PublicWorkEditorInput,
    PublicWorkEditorView,
)
from app.modules.public.media_service import PublicMediaInput
from app.modules.public.models import PublicationStatus
from app.modules.public.publication_dependencies import (
    PublicationServiceDependency,
    PublicMediaServiceDependency,
    PublicWorkEditorServiceDependency,
    TaxonomyServiceDependency,
)
from app.modules.public.schemas import (
    FeaturedWindowRequest,
    PublicationChecklistData,
    PublicationReasonRequest,
    PublicationRequest,
    PublicationScheduleRequest,
    PublicationVersionRequest,
    PublicMediaAdminData,
    PublicMediaAttachRequest,
    PublicMediaOrderRequest,
    PublicWorkAdminData,
    PublicWorkEditorData,
    PublicWorkEditorRequest,
    PublicWorkPreviewData,
    TaxonomyCategoryData,
    TaxonomyCategoryRequest,
    TaxonomyTagData,
    TaxonomyTagRequest,
    WorkTagAssignmentRequest,
)
from app.modules.public.taxonomy_service import CategoryInput, TagInput

router = APIRouter(
    prefix="/api/v1/admin/public-works",
    tags=["public-works-admin"],
)


def _response(
    row: object,
    request: Request,
) -> SuccessEnvelope[PublicWorkAdminData]:
    return SuccessEnvelope(
        data=PublicWorkAdminData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/{work_id}/publish", response_model=SuccessEnvelope[PublicWorkAdminData])
async def publish_public_work(
    work_id: UUID,
    payload: PublicationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicationServiceDependency,
) -> SuccessEnvelope[PublicWorkAdminData]:
    row = await service.publish(
        principal,
        work_id,
        expected_version=payload.expected_version,
        visibility=payload.visibility,
        request_id=request.state.request_id,
    )
    return _response(row, request)


@router.post("/{work_id}/schedule", response_model=SuccessEnvelope[PublicWorkAdminData])
async def schedule_public_work(
    work_id: UUID,
    payload: PublicationScheduleRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicationServiceDependency,
) -> SuccessEnvelope[PublicWorkAdminData]:
    row = await service.schedule(
        principal,
        work_id,
        expected_version=payload.expected_version,
        visibility=payload.visibility,
        publish_at=payload.publish_at,
        request_id=request.state.request_id,
    )
    return _response(row, request)


@router.post("/{work_id}/hide", response_model=SuccessEnvelope[PublicWorkAdminData])
async def hide_public_work(
    work_id: UUID,
    payload: PublicationVersionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicationServiceDependency,
) -> SuccessEnvelope[PublicWorkAdminData]:
    row = await service.hide(
        principal,
        work_id,
        expected_version=payload.expected_version,
        request_id=request.state.request_id,
    )
    return _response(row, request)


@router.post("/{work_id}/suspend", response_model=SuccessEnvelope[PublicWorkAdminData])
async def suspend_public_work(
    work_id: UUID,
    payload: PublicationReasonRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicationServiceDependency,
) -> SuccessEnvelope[PublicWorkAdminData]:
    row = await service.suspend(
        principal,
        work_id,
        expected_version=payload.expected_version,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return _response(row, request)


@router.post("/{work_id}/archive", response_model=SuccessEnvelope[PublicWorkAdminData])
async def archive_public_work(
    work_id: UUID,
    payload: PublicationReasonRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicationServiceDependency,
) -> SuccessEnvelope[PublicWorkAdminData]:
    row = await service.archive(
        principal,
        work_id,
        expected_version=payload.expected_version,
        reason=payload.reason,
        request_id=request.state.request_id,
    )
    return _response(row, request)


@router.post("/{work_id}/feature", response_model=SuccessEnvelope[PublicWorkAdminData])
async def feature_public_work(
    work_id: UUID,
    payload: FeaturedWindowRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicationServiceDependency,
) -> SuccessEnvelope[PublicWorkAdminData]:
    row = await service.feature(
        principal,
        work_id,
        expected_version=payload.expected_version,
        featured_at=payload.featured_at,
        featured_until=payload.featured_until,
        request_id=request.state.request_id,
    )
    return _response(row, request)


@router.post(
    "/{work_id}/unfeature", response_model=SuccessEnvelope[PublicWorkAdminData]
)
async def unfeature_public_work(
    work_id: UUID,
    payload: PublicationVersionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicationServiceDependency,
) -> SuccessEnvelope[PublicWorkAdminData]:
    row = await service.unfeature(
        principal,
        work_id,
        expected_version=payload.expected_version,
        request_id=request.state.request_id,
    )
    return _response(row, request)


@router.get("/categories", response_model=SuccessEnvelope[list[TaxonomyCategoryData]])
async def admin_categories(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: TaxonomyServiceDependency,
) -> SuccessEnvelope[list[TaxonomyCategoryData]]:
    rows = await service.list_admin_categories(principal)
    return SuccessEnvelope(
        data=[TaxonomyCategoryData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/categories",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[TaxonomyCategoryData],
)
async def create_category(
    payload: TaxonomyCategoryRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: TaxonomyServiceDependency,
) -> SuccessEnvelope[TaxonomyCategoryData]:
    row = await service.create_category(
        principal,
        CategoryInput(
            payload.name,
            payload.slug,
            payload.description,
            payload.parent_id,
            payload.display_order,
            payload.is_active,
            payload.code,
        ),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=TaxonomyCategoryData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch(
    "/categories/{category_id}",
    response_model=SuccessEnvelope[TaxonomyCategoryData],
)
async def update_category(
    category_id: UUID,
    payload: TaxonomyCategoryRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: TaxonomyServiceDependency,
) -> SuccessEnvelope[TaxonomyCategoryData]:
    row = await service.update_category(
        principal,
        category_id,
        CategoryInput(
            payload.name,
            payload.slug,
            payload.description,
            payload.parent_id,
            payload.display_order,
            payload.is_active,
            payload.code,
        ),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=TaxonomyCategoryData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/tags", response_model=SuccessEnvelope[list[TaxonomyTagData]])
async def admin_tags(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: TaxonomyServiceDependency,
) -> SuccessEnvelope[list[TaxonomyTagData]]:
    rows = await service.list_admin_tags(principal)
    return SuccessEnvelope(
        data=[TaxonomyTagData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/tags",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[TaxonomyTagData],
)
async def create_tag(
    payload: TaxonomyTagRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: TaxonomyServiceDependency,
) -> SuccessEnvelope[TaxonomyTagData]:
    row = await service.create_tag(
        principal,
        TagInput(payload.name, payload.slug, payload.is_active),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=TaxonomyTagData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch("/tags/{tag_id}", response_model=SuccessEnvelope[TaxonomyTagData])
async def update_tag(
    tag_id: UUID,
    payload: TaxonomyTagRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: TaxonomyServiceDependency,
) -> SuccessEnvelope[TaxonomyTagData]:
    row = await service.update_tag(
        principal,
        tag_id,
        TagInput(payload.name, payload.slug, payload.is_active),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=TaxonomyTagData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put("/{work_id}/tags", status_code=status.HTTP_204_NO_CONTENT)
async def assign_work_tags(
    work_id: UUID,
    payload: WorkTagAssignmentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: TaxonomyServiceDependency,
) -> None:
    await service.assign_tags(
        principal,
        work_id,
        tuple(payload.tag_ids),
        request_id=request.state.request_id,
    )


@router.get(
    "/{work_id}/media",
    response_model=SuccessEnvelope[list[PublicMediaAdminData]],
)
async def list_public_work_media(
    work_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PublicMediaServiceDependency,
) -> SuccessEnvelope[list[PublicMediaAdminData]]:
    rows = await service.list_admin(principal, work_id)
    return SuccessEnvelope(
        data=[PublicMediaAdminData.model_validate(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{work_id}/media",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[PublicMediaAdminData],
)
async def attach_public_work_media(
    work_id: UUID,
    payload: PublicMediaAttachRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicMediaServiceDependency,
) -> SuccessEnvelope[PublicMediaAdminData]:
    row = await service.attach(
        principal,
        work_id,
        PublicMediaInput(
            media_asset_id=payload.media_asset_id,
            sort_order=payload.sort_order,
            caption=payload.caption,
            alt_text=payload.alt_text,
        ),
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=PublicMediaAdminData.model_validate(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put("/{work_id}/media/order", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_public_work_media(
    work_id: UUID,
    payload: PublicMediaOrderRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicMediaServiceDependency,
) -> None:
    await service.reorder(
        principal,
        work_id,
        tuple(payload.relation_ids),
        request_id=request.state.request_id,
    )


@router.delete("/{work_id}/media/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_public_work_media(
    work_id: UUID,
    relation_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicMediaServiceDependency,
) -> None:
    await service.remove(
        principal,
        work_id,
        relation_id,
        request_id=request.state.request_id,
    )


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[PublicWorkAdminData]],
)
async def list_public_work_drafts(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PublicWorkEditorServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    query: Annotated[str | None, Query(max_length=120)] = None,
    publication_status: Annotated[
        PublicationStatus | None, Query(alias="status")
    ] = None,
) -> PaginatedSuccessEnvelope[list[PublicWorkAdminData]]:
    rows, total = await service.list(
        principal,
        query=query,
        status=publication_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[PublicWorkAdminData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


def _editor_data(view: PublicWorkEditorView) -> PublicWorkEditorData:
    work = view.work
    return PublicWorkEditorData(
        id=work.id,
        dossier_id=work.dossier_id,
        certificate_id=work.certificate_id,
        slug=work.slug,
        title=work.title,
        short_description=work.short_description,
        full_description=work.full_description,
        author_display_name=work.author_display_name,
        category_id=work.category_id,
        category_name=view.category_name,
        tag_ids=list(view.tag_ids),
        thumbnail_media_id=work.thumbnail_media_id,
        publication_status=work.publication_status,
        visibility=work.visibility,
        published_at=work.published_at,
        scheduled_publish_at=work.scheduled_publish_at,
        featured_at=work.featured_at,
        featured_until=work.featured_until,
        version=work.version,
        checklist=[
            PublicationChecklistData.model_validate(item) for item in view.checklist
        ],
    )


@router.get("/{work_id}", response_model=SuccessEnvelope[PublicWorkEditorData])
async def get_public_work_editor(
    work_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PublicWorkEditorServiceDependency,
) -> SuccessEnvelope[PublicWorkEditorData]:
    view = await service.get(principal, work_id)
    return SuccessEnvelope(
        data=_editor_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.patch("/{work_id}", response_model=SuccessEnvelope[PublicWorkEditorData])
async def update_public_work_editor(
    work_id: UUID,
    payload: PublicWorkEditorRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicWorkEditorServiceDependency,
) -> SuccessEnvelope[PublicWorkEditorData]:
    await service.update(
        principal,
        work_id,
        PublicWorkEditorInput(
            expected_version=payload.expected_version,
            slug=payload.slug,
            title=payload.title,
            short_description=payload.short_description,
            full_description=payload.full_description,
            author_display_name=payload.author_display_name,
            category_id=payload.category_id,
            tag_ids=tuple(payload.tag_ids),
            visibility=payload.visibility,
            thumbnail_media_id=payload.thumbnail_media_id,
        ),
        request_id=request.state.request_id,
    )
    view = await service.get(principal, work_id)
    return SuccessEnvelope(
        data=_editor_data(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{work_id}/preview",
    response_model=SuccessEnvelope[PublicWorkPreviewData],
)
async def preview_public_work_editor(
    work_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PublicWorkEditorServiceDependency,
) -> SuccessEnvelope[PublicWorkPreviewData]:
    view = await service.preview(principal, work_id)
    return SuccessEnvelope(
        data=PublicWorkPreviewData.model_validate(view),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
