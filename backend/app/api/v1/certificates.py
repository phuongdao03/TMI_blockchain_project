from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.schemas import (
    ErrorEnvelope,
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import CurrentPrincipalDependency
from app.modules.certificates.dependencies import CertificateServiceDependency
from app.modules.certificates.schemas import (
    CertificateData,
    CertificateDetailData,
    CertificateDownloadData,
)

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])

RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Certificate access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Certificate not found.", "model": ErrorEnvelope},
    409: {"description": "Certificate is not ready.", "model": ErrorEnvelope},
}


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[CertificateData]],
    responses=RESPONSES,
)
async def list_certificates(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[CertificateData]]:
    rows, total = await service.list(
        principal,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[CertificateData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/{certificate_id}",
    response_model=SuccessEnvelope[CertificateDetailData],
    responses=RESPONSES,
)
async def get_certificate(
    certificate_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateServiceDependency,
) -> SuccessEnvelope[CertificateDetailData]:
    detail = await service.get(principal, certificate_id)
    return SuccessEnvelope(
        data=CertificateDetailData(
            certificate=CertificateData.model_validate(detail.certificate),
            metadata=detail.metadata,
            metadata_hash=detail.metadata_hash,
            qr_payload=detail.qr_payload,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{certificate_id}/download",
    response_model=SuccessEnvelope[CertificateDownloadData],
    responses=RESPONSES,
)
async def download_certificate(
    certificate_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateServiceDependency,
) -> SuccessEnvelope[CertificateDownloadData]:
    download = await service.download(principal, certificate_id)
    return SuccessEnvelope(
        data=CertificateDownloadData.model_validate(download),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
