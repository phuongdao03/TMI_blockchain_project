from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SettingsDependency,
)
from app.modules.blockchain.schemas import DocumentVerificationData
from app.modules.blockchain.verification_dependencies import (
    DocumentVerificationServiceDependency,
)
from app.modules.media.dependencies import (
    MediaServiceDependency,
    enforce_upload_signature_rate_limit,
)
from app.modules.media.schemas import (
    CompleteUploadRequest,
    MediaActionData,
    MediaAssetData,
    SignedDeliveryData,
    UploadSignatureData,
    UploadSignatureRequest,
)
from app.modules.media.types import UploadCompletion, UploadIntent

router = APIRouter(prefix="/api/v1/media", tags=["media"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Media access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Media asset not found.", "model": ErrorEnvelope},
    409: {"description": "Media state conflict.", "model": ErrorEnvelope},
    422: {"description": "Media request is invalid.", "model": ErrorEnvelope},
    503: {"description": "Media provider is unavailable.", "model": ErrorEnvelope},
}


@router.post(
    "/upload-signature",
    dependencies=[Depends(enforce_upload_signature_rate_limit)],
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[UploadSignatureData],
    responses=PRIVATE_RESPONSES,
)
async def create_upload_signature(
    payload: UploadSignatureRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: MediaServiceDependency,
) -> SuccessEnvelope[UploadSignatureData]:
    issued = await service.create_upload_signature(
        principal,
        UploadIntent(
            purpose=payload.purpose,
            filename=payload.filename,
            mime_type=payload.mime_type,
            size=payload.size,
            confidentiality=payload.confidentiality,
        ),
    )
    return SuccessEnvelope(
        data=UploadSignatureData.model_validate(issued),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/complete",
    response_model=SuccessEnvelope[MediaAssetData],
    responses=PRIVATE_RESPONSES,
)
async def complete_upload(
    payload: CompleteUploadRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: MediaServiceDependency,
) -> SuccessEnvelope[MediaAssetData]:
    asset = await service.complete_upload(
        principal,
        UploadCompletion(
            media_id=payload.media_id,
            public_id=payload.public_id,
            version=payload.version,
            signature=payload.signature,
        ),
    )
    return SuccessEnvelope(
        data=MediaAssetData.model_validate(asset),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{media_id}",
    response_model=SuccessEnvelope[MediaAssetData],
    responses=PRIVATE_RESPONSES,
)
async def get_asset(
    media_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: MediaServiceDependency,
) -> SuccessEnvelope[MediaAssetData]:
    asset = await service.get_asset(principal, media_id)
    return SuccessEnvelope(
        data=MediaAssetData.model_validate(asset),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{media_id}/signed-url",
    response_model=SuccessEnvelope[SignedDeliveryData],
    responses=PRIVATE_RESPONSES,
)
async def create_signed_url(
    media_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: MediaServiceDependency,
) -> SuccessEnvelope[SignedDeliveryData]:
    delivery = await service.create_signed_url(principal, media_id)
    return SuccessEnvelope(
        data=SignedDeliveryData.model_validate(delivery),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/{media_id}/content",
    response_class=StreamingResponse,
    responses=PRIVATE_RESPONSES,
)
async def download_content(
    media_id: UUID,
    principal: CurrentPrincipalDependency,
    service: MediaServiceDependency,
) -> StreamingResponse:
    delivery = await service.download_content(principal, media_id)
    filename = quote(delivery.filename, safe="")
    return StreamingResponse(
        iter((delivery.content,)),
        media_type=delivery.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "private, no-store",
        },
    )


@router.post(
    "/{media_id}/verifications",
    response_model=SuccessEnvelope[DocumentVerificationData],
    responses={
        415: {
            "description": "A binary document body is required.",
            "model": ErrorEnvelope,
        },
        413: {
            "description": "The verification document is too large.",
            "model": ErrorEnvelope,
        },
        **PRIVATE_RESPONSES,
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        }
    },
)
async def verify_document_candidate(
    media_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    settings: SettingsDependency,
    service: DocumentVerificationServiceDependency,
) -> SuccessEnvelope[DocumentVerificationData]:
    if request.headers.get("content-type") != "application/octet-stream":
        raise HTTPException(
            status_code=415,
            detail="A binary document body is required.",
        )
    content_length = request.headers.get("content-length")
    if (
        content_length is not None
        and content_length.isdecimal()
        and int(content_length) > settings.document_verification_max_bytes
    ):
        raise HTTPException(
            status_code=413,
            detail="The document exceeds the verification size limit.",
        )
    result = await service.verify(principal, media_id, request.stream())
    return SuccessEnvelope(
        data=DocumentVerificationData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/{media_id}",
    response_model=SuccessEnvelope[MediaActionData],
    responses=PRIVATE_RESPONSES,
)
async def delete_asset(
    media_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: MediaServiceDependency,
) -> SuccessEnvelope[MediaActionData]:
    await service.delete_asset(principal, media_id)
    return SuccessEnvelope(
        data=MediaActionData(status="deleted"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
