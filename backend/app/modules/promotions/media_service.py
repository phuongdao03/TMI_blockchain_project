import hashlib
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.promotions.media_models import PromotionMediaAsset


def _invalid(
    message: str = "Ảnh không hợp lệ. Chỉ hỗ trợ PNG, JPEG hoặc WebP.",
) -> DomainError:
    return DomainError(code="PROMOTION_MEDIA_INVALID", message=message, status_code=422)


@dataclass(frozen=True)
class NormalizedImage:
    data: bytes
    mime_type: str
    width: int
    height: int


def normalize_image(body: bytes, *, max_bytes: int, max_pixels: int) -> NormalizedImage:
    if not body or len(body) > max_bytes:
        raise _invalid("Ảnh vượt quá giới hạn dung lượng cho phép.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(body)) as source:
                if source.format not in {"PNG", "JPEG", "WEBP"}:
                    raise _invalid()
                width, height = source.size
                if width < 1 or height < 1 or width * height > max_pixels:
                    raise _invalid("Kích thước ảnh vượt giới hạn cho phép.")
                source.verify()
            with Image.open(BytesIO(body)) as source:
                # Decode and rebuild pixels instead of copying EXIF/PNG text or
                # trusting a filename or browser Content-Type. Single-frame
                # re-encoding also removes animated/polyglot payloads.
                oriented = ImageOps.exif_transpose(source)
                clean = Image.new("RGBA", oriented.size)
                clean.paste(oriented.convert("RGBA"))
                output = BytesIO()
                clean.save(output, format="WEBP", quality=90, method=4)
                data = output.getvalue()
                if len(data) > max_bytes:
                    raise _invalid("Ảnh sau tối ưu vẫn vượt giới hạn dung lượng.")
                return NormalizedImage(
                    data=data,
                    mime_type="image/webp",
                    width=clean.width,
                    height=clean.height,
                )
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise _invalid() from error


class PromotionMediaService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        max_bytes: int = 5_242_880,
        max_pixels: int = 24_000_000,
    ) -> None:
        self.session = session
        self.max_bytes = max_bytes
        self.max_pixels = max_pixels

    async def upload(
        self, *, body: bytes, filename: str, alt_text: str, actor_id: UUID
    ) -> PromotionMediaAsset:
        recent = await self.session.scalar(
            select(func.count())
            .select_from(PromotionMediaAsset)
            .where(
                PromotionMediaAsset.created_by == actor_id,
                PromotionMediaAsset.created_at
                >= datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        if int(recent or 0) >= 30:
            raise DomainError(
                code="PROMOTION_MEDIA_RATE_LIMIT",
                message="Bạn tải ảnh quá nhanh. Vui lòng thử lại sau một phút.",
                status_code=429,
            )
        if (
            len(filename) > 255
            or not filename.strip()
            or "/" in filename
            or "\\" in filename
            or any(ord(c) < 32 for c in filename)
        ):
            raise _invalid("Tên tệp không hợp lệ.")
        if not alt_text.strip() or len(alt_text) > 500:
            raise _invalid("Mô tả ảnh phải có từ 1 đến 500 ký tự.")
        image = normalize_image(
            body, max_bytes=self.max_bytes, max_pixels=self.max_pixels
        )
        asset = PromotionMediaAsset(
            original_filename=filename,
            alt_text=alt_text.strip(),
            mime_type=image.mime_type,
            width=image.width,
            height=image.height,
            size=len(image.data),
            sha256=hashlib.sha256(image.data).hexdigest(),
            content=image.data,
            created_by=actor_id,
        )
        self.session.add(asset)
        await self.session.flush()
        AuditService(self.session).record(
            actor_user_id=actor_id,
            action="promotion.media.uploaded",
            resource_type="promotion_media",
            resource_id=str(asset.id),
            after={"size": asset.size, "width": asset.width, "height": asset.height},
        )
        await self.session.commit()
        await self.session.refresh(asset, attribute_names=["content"])
        return asset

    async def list(
        self, *, page: int, page_size: int
    ) -> tuple[list[PromotionMediaAsset], int]:
        where = PromotionMediaAsset.deleted_at.is_(None)
        total = await self.session.scalar(
            select(func.count()).select_from(PromotionMediaAsset).where(where)
        )
        rows = await self.session.scalars(
            select(PromotionMediaAsset)
            .where(where)
            .order_by(PromotionMediaAsset.created_at.desc(), PromotionMediaAsset.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), int(total or 0)

    async def public_asset(self, asset_id: UUID) -> PromotionMediaAsset:
        asset = await self.session.scalar(
            select(PromotionMediaAsset)
            .where(PromotionMediaAsset.id == asset_id)
            .options(undefer(PromotionMediaAsset.content))
        )
        if asset is None:
            raise DomainError(
                code="PROMOTION_MEDIA_NOT_FOUND",
                message="Không tìm thấy ảnh.",
                status_code=404,
            )
        return asset

    async def delete(self, asset_id: UUID, *, actor_id: UUID) -> None:
        asset = await self.public_asset(asset_id)
        if asset.deleted_at is None:
            asset.deleted_at = datetime.now(UTC)
            AuditService(self.session).record(
                actor_user_id=actor_id,
                action="promotion.media.deleted",
                resource_type="promotion_media",
                resource_id=str(asset.id),
                after={"deleted": True},
            )
            await self.session.commit()
