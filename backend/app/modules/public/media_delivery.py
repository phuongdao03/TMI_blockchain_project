from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import CertificateStatus
from app.modules.media.encryption import DocumentEncryptionKeyring
from app.modules.media.gateway import CloudinaryMediaGateway
from app.modules.media.models import MediaAsset, MediaEncryptionStatus, MediaStatus
from app.modules.media.retained_content import read_retained_content
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.errors import PublicWorkNotFoundError
from app.modules.public.media_repository import PublicMediaRepository
from app.modules.public.media_service import (
    VIDEO_QUALITY_TRANSFORMATIONS,
    PublicMediaService,
)
from app.modules.public.models import (
    DerivativeStatus,
    PublicationStatus,
    PublicWorkVisibility,
)
from app.modules.public.retained_video_cache import retained_video_cache
from app.modules.public.video_poster import (
    cached_poster,
    extract_video_poster,
    retain_poster,
)


def content_response(
    content: bytes, mime_type: str, byte_range: str | None
) -> Response:
    size = len(content)
    headers = {
        "Cache-Control": "private, no-store",
        "Accept-Ranges": "bytes",
        "X-Content-Type-Options": "nosniff",
    }
    if byte_range is None:
        return Response(content, media_type=mime_type, headers=headers)
    try:
        if not byte_range.startswith("bytes=") or "," in byte_range:
            raise ValueError()
        first, last = byte_range[6:].split("-", 1)
        if first:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        else:
            suffix = int(last)
            if suffix <= 0:
                raise ValueError()
            start, end = max(0, size - suffix), size - 1
        if start < 0 or start >= size or end < start:
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"}
        ) from None
    headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return Response(
        content[start : end + 1], status_code=206, media_type=mime_type, headers=headers
    )


class PublicMediaDeliveryService:
    def __init__(
        self,
        session: AsyncSession,
        gateway: CloudinaryMediaGateway,
        keyring: DocumentEncryptionKeyring | None,
    ) -> None:
        self.session, self.gateway, self.keyring = session, gateway, keyring

    async def deliver(
        self,
        work_id: UUID,
        relation_id: UUID,
        principal: AuthPrincipal | None,
        byte_range: str | None,
        *,
        poster: bool = False,
        poster_time_ms: int | None = None,
    ) -> Response:
        repository = PublicMediaRepository(self.session)
        async with self.session.begin():
            joined = await repository.get_relation_with_asset(relation_id)
            context = await PublicWorkRepository(self.session).get_publication_context(
                work_id
            )
            if joined is None or context is None:
                raise PublicWorkNotFoundError()
            relation, asset = joined
            work = context.work
            if (
                relation.public_work_id != work_id
                or asset.status is not MediaStatus.ACTIVE
                or asset.deleted_at is not None
                or asset.access_mode != "authenticated"
                or asset.encryption_status
                not in {
                    MediaEncryptionStatus.ENCRYPTED,
                    MediaEncryptionStatus.NOT_REQUIRED,
                    MediaEncryptionStatus.LEGACY_UNENCRYPTED,
                }
                or relation.derivative_status is not DerivativeStatus.READY
                or not await repository.is_source_evidence_asset(work, asset.id)
            ):
                raise PublicWorkNotFoundError()
            anonymous_allowed = (
                work.publication_status is PublicationStatus.PUBLISHED
                and work.published_at is not None
                and work.visibility
                in {PublicWorkVisibility.PUBLIC, PublicWorkVisibility.UNLISTED}
                and context.category.is_active
                and context.certificate is not None
                and context.certificate.status is CertificateStatus.ACTIVE
                and context.certificate.dossier_id == work.dossier_id
                and (
                    context.certificate.expires_at is None
                    or context.certificate.expires_at.replace(tzinfo=UTC)
                    > datetime.now(UTC)
                )
            )
            if not anonymous_allowed:
                if principal is None:
                    raise PublicWorkNotFoundError()
                PublicMediaService._require_admin(principal)
        if poster and not asset.mime_type.startswith("video/"):
            raise PublicWorkNotFoundError()
        duration = getattr(relation, "duration_ms", None) or getattr(
            asset, "duration_ms", None
        )
        selected_time = (
            poster_time_ms
            if poster_time_ms is not None
            else getattr(relation, "poster_time_ms", None)
        )
        if selected_time is None:
            selected_time = min(int(duration * 0.25), 30_000) if duration else 0
        if poster and (
            not 0 <= selected_time <= 86_400_000
            or (duration is not None and selected_time >= duration)
        ):
            raise HTTPException(
                status_code=422, detail="Thời điểm ảnh bìa nằm ngoài video."
            )
        if asset.encryption_status is not MediaEncryptionStatus.ENCRYPTED:
            formats = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
                "video/mp4": "mp4",
                "video/webm": "webm",
                "audio/mpeg": "mp3",
                "audio/mp4": "m4a",
                "audio/ogg": "ogg",
                "application/pdf": "pdf",
            }
            file_format = formats.get(asset.mime_type)
            if file_format is None or asset.sha256 is None:
                raise PublicWorkNotFoundError()
            transformation = (
                f"so_{selected_time / 1000:g},c_limit,w_960,q_auto"
                if poster
                else f"c_limit,w_{relation.video_max_width},"
                f"{VIDEO_QUALITY_TRANSFORMATIONS[relation.video_quality_profile]},vc_auto"
                if asset.mime_type.startswith("video/")
                else None
            )
            url = self.gateway.create_signed_delivery_url(
                public_id=asset.cloudinary_public_id,
                resource_type=asset.resource_type,
                file_format="jpg" if poster else file_format,
                expires_at=int(datetime.now(UTC).timestamp()) + 300,
                transformation=transformation,
            )
            return RedirectResponse(
                url, status_code=307, headers={"Cache-Control": "private, no-store"}
            )
        if poster:
            # Authorization above always runs, including on cache hits.
            digest = (
                f"{asset.id}:{asset.sha256}:{selected_time}" if asset.sha256 else None
            )
            frame = cached_poster(digest)
            if frame is None:
                content = await self._retained_video(asset)
                frame = await extract_video_poster(content, selected_time / 1000)
                retain_poster(digest, frame)
            return Response(
                frame,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        content = (
            await self._retained_video(asset)
            if asset.mime_type.startswith("video/")
            else await read_retained_content(asset, self.gateway, self.keyring)
        )
        return content_response(content, asset.mime_type, byte_range)

    async def _retained_video(self, asset: MediaAsset) -> bytes:
        key = ":".join(
            str(getattr(asset, name, None))
            for name in (
                "id",
                "sha256",
                "encryption_key_id",
                "encryption_nonce",
                "encryption_tag",
                "cloudinary_public_id",
            )
        )
        return await retained_video_cache.get(
            key, lambda: read_retained_content(asset, self.gateway, self.keyring)
        )
