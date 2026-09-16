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
    CertificateServiceDependency,
    CertificateVersionServiceDependency,
)
from app.modules.certificates.schemas import (
    AdminCertificateData,
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
