from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

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
from app.modules.blockchain.models import CertificateStatus
from app.modules.certificates.dependencies import (
    CertificateContentServiceDependency,
    CertificateServiceDependency,
    CertificateVersionServiceDependency,
)
from app.modules.certificates.schemas import (
    AdminCertificateData,
    CertificateContentCorrectionRequest,
    CertificateContentDraftData,
    CertificateContentRequest,
    CertificateIssuedContentData,
    CertificateListingData,
    CertificateListingRequest,
    CertificateRevocationRequest,
    CertificateVersionData,
)
from app.modules.public.models import PublicationStatus
from app.modules.public.publication_dependencies import (
    PublicWorkEditorServiceDependency,
)

router = APIRouter(
    prefix="/api/v1/admin/certificates",
    tags=["certificate-revocations"],
)

RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Certificate access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Certificate not found.", "model": ErrorEnvelope},
    409: {"description": "Certificate state conflicts.", "model": ErrorEnvelope},
}


@router.get(
    "/content-drafts",
    response_model=SuccessEnvelope[list[CertificateContentDraftData]],
    responses=RESPONSES,
)
async def list_certificate_content_drafts(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateContentServiceDependency,
) -> SuccessEnvelope[list[CertificateContentDraftData]]:
    rows = await service.list_drafts(principal)
    return SuccessEnvelope(
        data=list(rows), meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.put(
    "/content-drafts/{dossier_id}",
    response_model=SuccessEnvelope[CertificateContentDraftData],
    responses=RESPONSES,
)
async def update_certificate_content_draft(
    dossier_id: UUID,
    payload: CertificateContentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CertificateContentServiceDependency,
) -> SuccessEnvelope[CertificateContentDraftData]:
    draft = await service.update(principal, dossier_id, payload)
    return SuccessEnvelope(
        data=draft, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/content-drafts/{dossier_id}/confirm",
    response_model=SuccessEnvelope[CertificateContentDraftData],
    responses=RESPONSES,
)
async def confirm_certificate_content_draft(
    dossier_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CertificateContentServiceDependency,
) -> SuccessEnvelope[CertificateContentDraftData]:
    draft = await service.confirm(principal, dossier_id)
    return SuccessEnvelope(
        data=draft, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get(
    "/{certificate_id}/content",
    response_model=SuccessEnvelope[CertificateIssuedContentData],
    responses=RESPONSES,
)
async def get_issued_certificate_content(
    certificate_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateVersionServiceDependency,
) -> SuccessEnvelope[CertificateIssuedContentData]:
    content = await service.current_content(principal, certificate_id)
    return SuccessEnvelope(
        data=content, meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/{certificate_id}/content-corrections",
    response_model=SuccessEnvelope[CertificateVersionData],
    status_code=status.HTTP_201_CREATED,
    responses=RESPONSES,
)
async def request_issued_certificate_content_correction(
    certificate_id: UUID,
    payload: CertificateContentCorrectionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: CertificateVersionServiceDependency,
) -> SuccessEnvelope[CertificateVersionData]:
    version = await service.request_content_correction(
        principal, certificate_id, payload
    )
    return SuccessEnvelope(
        data=CertificateVersionData.model_validate(version),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[AdminCertificateData]],
    responses=RESPONSES,
)
async def list_admin_certificates(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=255),
    certificate_status: Annotated[
        CertificateStatus | None, Query(alias="status")
    ] = None,
    publication_status: Annotated[
        PublicationStatus | None, Query(alias="publicationStatus")
    ] = None,
) -> PaginatedSuccessEnvelope[list[AdminCertificateData]]:
    rows, total = await service.list_admin(
        principal,
        search=search,
        status=certificate_status.value if certificate_status else None,
        publication_status=publication_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[AdminCertificateData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.patch(
    "/{certificate_id}/listing",
    response_model=SuccessEnvelope[CertificateListingData],
    responses=RESPONSES,
)
async def configure_certificate_listing(
    certificate_id: UUID,
    payload: CertificateListingRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PublicWorkEditorServiceDependency,
) -> SuccessEnvelope[CertificateListingData]:
    work = await service.configure_certificate_listing(
        principal,
        certificate_id,
        expected_version=payload.expected_work_version,
        show=payload.show_certificate,
        request_id=request.state.request_id,
    )
    return SuccessEnvelope(
        data=CertificateListingData(
            show_certificate=work.show_certificate, public_work_version=work.version
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/{certificate_id}/revocations",
    response_model=SuccessEnvelope[CertificateVersionData],
    status_code=status.HTTP_202_ACCEPTED,
    responses=RESPONSES,
)
async def request_certificate_revocation(
    certificate_id: UUID,
    payload: CertificateRevocationRequest,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateVersionServiceDependency,
) -> SuccessEnvelope[CertificateVersionData]:
    version = await service.revoke(
        principal,
        certificate_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=CertificateVersionData.model_validate(version),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
