from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
    SettingsDependency,
)
from app.modules.promotions.admin_access import require_promotion_access
from app.modules.promotions.media_models import PromotionMediaAsset
from app.modules.promotions.media_service import PromotionMediaService
from app.modules.promotions.rate_limit import enforce_promotion_rate_limit

router = APIRouter(
    prefix="/api/v1/admin/promotion-media",
    tags=["promotion-media"],
    dependencies=[Depends(enforce_promotion_rate_limit)],
)
public_router = APIRouter(prefix="/api/v1/promotion-media", tags=["promotion-media"])


class MediaData(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID
    url: str
    mime_type: str = Field(alias="mimeType")
    width: int
    height: int
    size: int
    alt_text: str = Field(alias="altText")


def media_data(asset: PromotionMediaAsset) -> MediaData:
    return MediaData(
        id=asset.id,
        url=f"/api/v1/promotion-media/{asset.id}",
        mimeType=asset.mime_type,
        width=asset.width,
        height=asset.height,
        size=asset.size,
        altText=asset.alt_text,
    )


def get_media_service(
    session: SessionDependency, settings: SettingsDependency
) -> PromotionMediaService:
    return PromotionMediaService(
        session,
        max_bytes=getattr(settings, "promotion_media_max_bytes", 5_242_880),
        max_pixels=getattr(settings, "promotion_media_max_pixels", 24_000_000),
    )


ServiceDependency = Annotated[PromotionMediaService, Depends(get_media_service)]


@router.get("")
async def list_media(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ServiceDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
) -> SuccessEnvelope[dict[str, object]]:
    require_promotion_access(principal, write=False)
    rows, total = await service.list(page=page, page_size=page_size)
    return SuccessEnvelope(
        data={
            "items": [
                media_data(row).model_dump(by_alias=True, mode="json") for row in rows
            ],
            "page": page,
            "pageSize": page_size,
            "total": total,
        },
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("", response_model=SuccessEnvelope[MediaData])
async def upload_media(
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
    filename: str = Query(min_length=1, max_length=255),
    alt_text: str = Query(min_length=1, max_length=500, alias="altText"),
) -> SuccessEnvelope[MediaData]:
    require_promotion_access(principal)
    # Bound the streaming read before buffering attacker-controlled bodies.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > service.max_bytes:
            from app.core.errors import DomainError

            raise DomainError(
                code="PROMOTION_MEDIA_TOO_LARGE",
                message="Ảnh vượt giới hạn dung lượng.",
                status_code=413,
            )
    asset = await service.upload(
        body=bytes(body),
        filename=filename,
        alt_text=alt_text,
        actor_id=principal.user_id,
    )
    return SuccessEnvelope(
        data=media_data(asset), meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.delete("/{asset_id}")
async def delete_media(
    asset_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
) -> SuccessEnvelope[dict[str, str]]:
    require_promotion_access(principal)
    await service.delete(asset_id, actor_id=principal.user_id)
    return SuccessEnvelope(
        data={"status": "deleted"},
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@public_router.get("/{asset_id}")
async def public_media(
    asset_id: UUID, request: Request, service: ServiceDependency
) -> Response:
    asset = await service.public_asset(asset_id)
    etag = f'"{asset.sha256}"'
    headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "ETag": etag,
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'",
        "Content-Disposition": f'inline; filename="{asset.id}.webp"',
    }
    if request.headers.get("If-None-Match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=asset.content, media_type=asset.mime_type, headers=headers)
