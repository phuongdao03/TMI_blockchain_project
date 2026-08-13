from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request, status

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import CurrentPrincipalDependency
from app.modules.certificates.dependencies import (
    CertificateVersionServiceDependency,
)
from app.modules.certificates.schemas import (
    CertificateRevocationRequest,
    CertificateVersionData,
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
