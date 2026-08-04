import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.media.errors import (
    MediaForbiddenError,
    MediaInvalidStateError,
    MediaNotFoundError,
    MediaSignatureInvalidError,
    MediaUploadMetadataMismatchError,
    MediaValidationError,
)
from app.modules.media.gateway import MediaGateway, ProviderAssetMetadata
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.repository import MediaAssetRepository
from app.modules.media.types import (
    MediaAssetView,
    MediaPurpose,
    SignedDeliveryView,
    UploadCompletion,
    UploadIntent,
    UploadSignatureView,
)

logger = logging.getLogger(__name__)


class MediaDeliveryAccessPolicy(Protocol):
    async def can_deliver(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class _FormatPolicy:
    file_format: str
    resource_type: str
    extensions: frozenset[str]


_FORMATS = {
    "image/jpeg": _FormatPolicy("jpg", "image", frozenset({".jpg", ".jpeg"})),
    "image/png": _FormatPolicy("png", "image", frozenset({".png"})),
    "image/webp": _FormatPolicy("webp", "image", frozenset({".webp"})),
    "application/pdf": _FormatPolicy("pdf", "raw", frozenset({".pdf"})),
    "audio/mpeg": _FormatPolicy("mp3", "video", frozenset({".mp3"})),
    "audio/mp4": _FormatPolicy("mp4", "video", frozenset({".m4a", ".mp4"})),
    "audio/ogg": _FormatPolicy("ogg", "video", frozenset({".ogg"})),
    "video/mp4": _FormatPolicy("mp4", "video", frozenset({".mp4"})),
    "video/webm": _FormatPolicy("webm", "video", frozenset({".webm"})),
}
_PURPOSE_MIME_TYPES = {
    MediaPurpose.AVATAR: frozenset({"image/jpeg", "image/png", "image/webp"}),
    MediaPurpose.DOSSIER_EVIDENCE: frozenset(_FORMATS),
    MediaPurpose.PUBLIC_WORK: frozenset(_FORMATS),
}


class MediaService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: MediaGateway,
        environment: str,
        signature_ttl_seconds: int,
        delivery_ttl_seconds: int,
        avatar_max_bytes: int,
        evidence_max_bytes: int,
        delivery_access_policy: MediaDeliveryAccessPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = MediaAssetRepository(session)
        self._gateway = gateway
        self._environment = environment
        self._signature_ttl_seconds = signature_ttl_seconds
        self._delivery_ttl_seconds = delivery_ttl_seconds
        self._max_bytes = {
            MediaPurpose.AVATAR: avatar_max_bytes,
            MediaPurpose.DOSSIER_EVIDENCE: evidence_max_bytes,
            MediaPurpose.PUBLIC_WORK: evidence_max_bytes,
        }
        self._delivery_access_policy = delivery_access_policy
        self._clock = clock or (lambda: datetime.now(UTC))

    async def create_upload_signature(
        self,
        principal: AuthPrincipal,
        intent: UploadIntent,
    ) -> UploadSignatureView:
        policy = self._validate_intent(intent)
        issued_at = int(self._clock().timestamp())
        media_id = uuid4()
        purpose_segment = intent.purpose.value.lower().replace("_", "-")
        public_id = (
            f"ip-certificate/{self._environment}/{principal.user_id}/"
            f"{purpose_segment}/{media_id}"
        )
        authorization = await self._gateway.create_upload_signature(
            public_id=public_id,
            resource_type=policy.resource_type,
            timestamp=issued_at,
            allowed_format=policy.file_format,
        )
        asset = MediaAsset(
            id=media_id,
            owner_user_id=principal.user_id,
            cloudinary_public_id=public_id,
            resource_type=policy.resource_type,
            access_mode="authenticated",
            original_filename=intent.filename,
            mime_type=intent.mime_type,
            bytes=intent.size,
        )
        async with self._session.begin():
            self._repository.add(asset)
            await self._session.flush()
        self._audit("media.upload_authorized", principal.user_id, media_id)
        return UploadSignatureView(
            media_id=media_id,
            public_id=public_id,
            upload_url=authorization.upload_url,
            cloud_name=authorization.cloud_name,
            api_key=authorization.api_key,
            signature=authorization.signature,
            parameters=authorization.parameters,
            expires_at=issued_at + self._signature_ttl_seconds,
        )

    async def complete_upload(
        self,
        principal: AuthPrincipal,
        completion: UploadCompletion,
    ) -> MediaAssetView:
        async with self._session.begin():
            asset = await self._owned_asset(principal, completion.media_id)
            if asset.status is not MediaStatus.PENDING:
                raise MediaInvalidStateError()
            if asset.cloudinary_public_id != completion.public_id:
                raise MediaUploadMetadataMismatchError()
            if not self._gateway.verify_upload_result(
                public_id=completion.public_id,
                version=completion.version,
                signature=completion.signature,
            ):
                raise MediaSignatureInvalidError()
            resource_type = asset.resource_type
        metadata = await self._gateway.get_asset_metadata(
            public_id=completion.public_id,
            resource_type=resource_type,
        )
        async with self._session.begin():
            asset = await self._owned_asset(
                principal,
                completion.media_id,
                for_update=True,
            )
            if asset.status is not MediaStatus.PENDING:
                raise MediaInvalidStateError()
            self._validate_provider_metadata(asset, completion, metadata)
            asset.cloudinary_version = metadata.version
            asset.bytes = metadata.bytes
            asset.width = metadata.width
            asset.height = metadata.height
            asset.duration_ms = metadata.duration_ms
            asset.sha256 = metadata.sha256
            asset.status = MediaStatus.ACTIVE
            await self._session.flush()
            view = self._view(asset)
        self._audit("media.upload_completed", principal.user_id, completion.media_id)
        return view

    async def create_signed_url(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> SignedDeliveryView:
        async with self._session.begin():
            asset = await self._deliverable_asset(principal, media_id)
            if asset.status is not MediaStatus.ACTIVE:
                raise MediaInvalidStateError()
            expires_at = int(self._clock().timestamp()) + self._delivery_ttl_seconds
            url = self._gateway.create_signed_delivery_url(
                public_id=asset.cloudinary_public_id,
                resource_type=asset.resource_type,
                file_format=_FORMATS[asset.mime_type].file_format,
                expires_at=expires_at,
            )
        self._audit("media.delivery_signed", principal.user_id, media_id)
        return SignedDeliveryView(url=url, expires_at=expires_at)

    async def delete_asset(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> None:
        async with self._session.begin():
            asset = await self._owned_asset(principal, media_id)
            if asset.status is MediaStatus.DELETED:
                raise MediaInvalidStateError()
            public_id = asset.cloudinary_public_id
            resource_type = asset.resource_type
        await self._gateway.delete_asset(
            public_id=public_id,
            resource_type=resource_type,
        )
        async with self._session.begin():
            asset = await self._owned_asset(principal, media_id, for_update=True)
            if asset.status is MediaStatus.DELETED:
                raise MediaInvalidStateError()
            asset.status = MediaStatus.DELETED
            asset.deleted_at = self._clock()
        self._audit("media.deleted", principal.user_id, media_id)

    def _validate_intent(self, intent: UploadIntent) -> _FormatPolicy:
        if intent.mime_type not in _PURPOSE_MIME_TYPES[intent.purpose]:
            raise MediaValidationError(
                "MIME type is not allowed for the requested purpose."
            )
        if intent.size <= 0 or intent.size > self._max_bytes[intent.purpose]:
            raise MediaValidationError(
                "File size is not allowed for the requested purpose."
            )
        if (
            not intent.filename
            or intent.filename != intent.filename.strip()
            or "/" in intent.filename
            or "\\" in intent.filename
            or any(ord(character) < 32 for character in intent.filename)
        ):
            raise MediaValidationError("Filename is invalid.")
        policy = _FORMATS[intent.mime_type]
        if PurePath(intent.filename).suffix.lower() not in policy.extensions:
            raise MediaValidationError("Filename extension does not match MIME type.")
        return policy

    @staticmethod
    def _validate_provider_metadata(
        asset: MediaAsset,
        completion: UploadCompletion,
        metadata: ProviderAssetMetadata,
    ) -> None:
        policy = _FORMATS[asset.mime_type]
        if (
            metadata.public_id != asset.cloudinary_public_id
            or metadata.version != completion.version
            or metadata.resource_type != asset.resource_type
            or metadata.delivery_type != asset.access_mode
            or metadata.file_format != policy.file_format
            or metadata.bytes != asset.bytes
            or (
                metadata.resource_type == "image"
                and (
                    metadata.width is None
                    or metadata.width <= 0
                    or metadata.height is None
                    or metadata.height <= 0
                )
            )
        ):
            raise MediaUploadMetadataMismatchError()

    async def _owned_asset(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
        *,
        for_update: bool = False,
    ) -> MediaAsset:
        asset = await self._repository.get_by_id(media_id, for_update=for_update)
        if asset is None:
            raise MediaNotFoundError()
        if asset.owner_user_id != principal.user_id:
            raise MediaForbiddenError()
        return asset

    async def _deliverable_asset(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> MediaAsset:
        asset = await self._repository.get_by_id(media_id)
        if asset is None:
            raise MediaNotFoundError()
        if asset.owner_user_id == principal.user_id:
            return asset
        if (
            self._delivery_access_policy is None
            or not await self._delivery_access_policy.can_deliver(
                principal,
                media_id,
            )
        ):
            raise MediaForbiddenError()
        return asset

    @staticmethod
    def _view(asset: MediaAsset) -> MediaAssetView:
        return MediaAssetView(
            id=asset.id,
            status=asset.status,
            mime_type=asset.mime_type,
            bytes=asset.bytes,
            width=asset.width,
            height=asset.height,
            duration_ms=asset.duration_ms,
        )

    @staticmethod
    def _audit(action: str, user_id: UUID, media_id: UUID) -> None:
        logger.info(
            "security_audit",
            extra={
                "action": action,
                "user_id": str(user_id),
                "media_id": str(media_id),
            },
        )

    async def close(self) -> None:
        await self._gateway.close()
        await self._session.close()
