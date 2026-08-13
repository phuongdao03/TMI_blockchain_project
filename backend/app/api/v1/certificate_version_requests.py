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
from app.modules.certificates.dependencies import (
    CertificateVersionServiceDependency,
)
from app.modules.certificates.schemas import (
    CertificateVersionData,
    CertificateVersionDecision,
    CertificateVersionDecisionRequest,
)

router = APIRouter(
    prefix="/api/v1/admin/certificate-version-requests",
    tags=["certificate-version-requests"],
)

RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Certificate access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Version request not found.", "model": ErrorEnvelope},
    409: {"description": "Version request state conflicts.", "model": ErrorEnvelope},
}


@router.get(
    "",
    response_model=PaginatedSuccessEnvelope[list[CertificateVersionData]],
    responses=RESPONSES,
)
async def list_certificate_version_requests(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateVersionServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PaginatedSuccessEnvelope[list[CertificateVersionData]]:
    rows, total = await service.list_requests(
        principal,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[CertificateVersionData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.patch(
    "/{version_id}",
    response_model=SuccessEnvelope[CertificateVersionData],
    responses=RESPONSES,
)
async def decide_certificate_version_request(
    version_id: UUID,
    payload: CertificateVersionDecisionRequest,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: CertificateVersionServiceDependency,
) -> SuccessEnvelope[CertificateVersionData]:
    if payload.decision is CertificateVersionDecision.APPROVE:
        version = await service.approve(principal, version_id)
    else:
        version = await service.reject(
            principal,
            version_id,
            reason=payload.reason or "",
        )
    return SuccessEnvelope(
        data=CertificateVersionData.model_validate(version),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
