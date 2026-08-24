import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from typing import Protocol
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.session_service import AuthPrincipal
from app.modules.media.encryption import (
    DocumentEncryptionConfigurationError,
    DocumentEncryptionKeyring,
    EncryptedDocument,
)
from app.modules.media.errors import (
    MediaForbiddenError,
    MediaInvalidStateError,
    MediaNotFoundError,
    MediaSignatureInvalidError,
    MediaUploadMetadataMismatchError,
    MediaValidationError,
)
from app.modules.media.gateway import (
    MediaContentTooLargeError,
    MediaGateway,
    ProviderAssetMetadata,
)
from app.modules.media.models import (
    MediaAsset,
    MediaConfidentiality,
    MediaEncryptionStatus,
    MediaStatus,
)
from app.modules.media.repository import MediaAssetRepository
from app.modules.media.types import (
    MediaAssetView,
    MediaContentView,
    MediaPurpose,
    SignedDeliveryView,
    UploadCompletion,
    UploadIntent,
    UploadSignatureView,
)


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
    "audio/wav": _FormatPolicy("wav", "video", frozenset({".wav"})),
    "audio/x-wav": _FormatPolicy("wav", "video", frozenset({".wav"})),
    "video/mp4": _FormatPolicy("mp4", "video", frozenset({".mp4"})),
    "video/webm": _FormatPolicy("webm", "video", frozenset({".webm"})),
    "application/msword": _FormatPolicy("doc", "raw", frozenset({".doc"})),
    "application/vnd.ms-excel": _FormatPolicy("xls", "raw", frozenset({".xls"})),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        _FormatPolicy("docx", "raw", frozenset({".docx"}))
    ),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
        _FormatPolicy("xlsx", "raw", frozenset({".xlsx"}))
    ),
    "application/zip": _FormatPolicy("zip", "raw", frozenset({".zip"})),
}
_EVIDENCE_ONLY_MIME_TYPES = frozenset(
    {
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    }
)
_PUBLIC_MEDIA_MIME_TYPES = frozenset(_FORMATS) - _EVIDENCE_ONLY_MIME_TYPES
_PURPOSE_MIME_TYPES = {
    MediaPurpose.AVATAR: frozenset({"image/jpeg", "image/png", "image/webp"}),
    MediaPurpose.DOSSIER_EVIDENCE: frozenset(_FORMATS),
    MediaPurpose.PUBLIC_WORK: _PUBLIC_MEDIA_MIME_TYPES,
}
_DANGEROUS_INNER_EXTENSIONS = frozenset(
    {
        ".bat",
        ".cmd",
        ".com",
        ".dll",
        ".exe",
        ".hta",
        ".jar",
        ".js",
        ".msi",
        ".ps1",
        ".scr",
        ".vbs",
    }
)


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
        enqueue_inspection: Callable[[UUID], object] | None = None,
        delivery_access_policy: MediaDeliveryAccessPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        encryption_keyring: DocumentEncryptionKeyring | None = None,
    ) -> None:
        self._session = session
        self._repository = MediaAssetRepository(session)
        self._audit_service = AuditService(session)
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
        self._enqueue_inspection = enqueue_inspection or (lambda _media_id: None)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._encryption_keyring = encryption_keyring

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
            max_bytes=intent.size,
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
            confidentiality=intent.confidentiality,
        )
        async with self._session.begin():
            self._repository.add(asset)
            self._audit(
                "media.upload_authorized",
                principal.user_id,
                media_id,
                status=MediaStatus.PENDING,
            )
            await self._session.flush()
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
        replay_view: MediaAssetView | None = None
        async with self._session.begin():
            asset = await self._owned_asset(principal, completion.media_id)
            if asset.status is MediaStatus.QUARANTINED:
                if asset.cloudinary_public_id != completion.public_id:
                    raise MediaUploadMetadataMismatchError()
                if not self._gateway.verify_upload_result(
                    public_id=completion.public_id,
                    version=completion.version,
                    signature=completion.signature,
                ):
                    raise MediaSignatureInvalidError()
                replay_view = self._view(asset)
                self._audit(
                    "media.inspection_requeued",
                    principal.user_id,
                    completion.media_id,
                    status=asset.status,
                )
            elif asset.status is not MediaStatus.PENDING:
                raise MediaInvalidStateError()
            elif asset.cloudinary_public_id != completion.public_id:
                raise MediaUploadMetadataMismatchError()
            elif not self._gateway.verify_upload_result(
                public_id=completion.public_id,
                version=completion.version,
                signature=completion.signature,
            ):
                raise MediaSignatureInvalidError()
            resource_type = asset.resource_type
        if replay_view is not None:
            self._enqueue_inspection(completion.media_id)
            return replay_view
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
            # Provider digests are advisory only. The trusted inspection worker
            # computes SHA-256 from the downloaded bytes before activation.
            asset.sha256 = None
            asset.status = MediaStatus.QUARANTINED
            self._audit(
                "media.upload_quarantined",
                principal.user_id,
                completion.media_id,
                status=asset.status,
            )
            await self._session.flush()
            view = self._view(asset)
        self._enqueue_inspection(completion.media_id)
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
            if (
                self._encryption_keyring is not None
                and asset.confidentiality is MediaConfidentiality.PRIVATE
                and asset.encryption_status is not MediaEncryptionStatus.ENCRYPTED
            ):
                raise MediaInvalidStateError()
            expires_at = int(self._clock().timestamp()) + self._delivery_ttl_seconds
            if asset.encryption_status is MediaEncryptionStatus.ENCRYPTED:
                url = f"/api/v1/media/{media_id}/content"
            else:
                url = self._gateway.create_signed_delivery_url(
                    public_id=asset.cloudinary_public_id,
                    resource_type=asset.resource_type,
                    file_format=_FORMATS[asset.mime_type].file_format,
                    expires_at=expires_at,
                )
            self._audit(
                "media.delivery_signed",
                principal.user_id,
                media_id,
                status=asset.status,
            )
        return SignedDeliveryView(url=url, expires_at=expires_at)

    async def download_content(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> MediaContentView:
        async with self._session.begin():
            asset = await self._deliverable_asset(principal, media_id)
            if (
                asset.status != MediaStatus.ACTIVE
                or asset.encryption_status != MediaEncryptionStatus.ENCRYPTED
                or asset.sha256 is None
                or asset.encryption_key_id is None
                or asset.encryption_nonce is None
                or asset.encryption_tag is None
                or asset.encrypted_object_public_id is None
                or asset.encrypted_bytes is None
            ):
                raise MediaInvalidStateError()
            snapshot = (
                asset.sha256,
                asset.encryption_key_id,
                asset.encryption_nonce,
                asset.encryption_tag,
                asset.encrypted_object_public_id,
                asset.encrypted_bytes,
                asset.mime_type,
                asset.original_filename,
            )
        (
            digest,
            key_id,
            nonce,
            tag,
            encrypted_public_id,
            encrypted_bytes,
            mime_type,
            filename,
        ) = snapshot
        try:
            ciphertext = await self._gateway.download_asset(
                public_id=encrypted_public_id,
                resource_type="raw",
                file_format="bin",
                max_bytes=encrypted_bytes,
            )
        except MediaContentTooLargeError:
            raise MediaInvalidStateError() from None
        if len(ciphertext) != encrypted_bytes or self._encryption_keyring is None:
            raise MediaInvalidStateError()
        try:
            content = self._encryption_keyring.decrypt(
                EncryptedDocument(
                    key_id=key_id,
                    nonce=nonce,
                    ciphertext=ciphertext,
                    tag=tag,
                ),
                media_id=media_id,
                sha256=digest,
            )
        except (InvalidTag, DocumentEncryptionConfigurationError):
            raise MediaInvalidStateError() from None
        if hashlib.sha256(content).hexdigest() != digest:
            raise MediaInvalidStateError()
        async with self._session.begin():
            asset = await self._deliverable_asset(principal, media_id)
            if asset.status is not MediaStatus.ACTIVE:
                raise MediaInvalidStateError()
            self._audit(
                "media.private_content_delivered",
                principal.user_id,
                media_id,
                status=asset.status,
            )
        return MediaContentView(
            content=content,
            mime_type=mime_type,
            filename=filename,
        )

    async def get_asset(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> MediaAssetView:
        async with self._session.begin():
            asset = await self._owned_asset(principal, media_id)
            return self._view(asset)

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
            if (
                asset.encryption_status is MediaEncryptionStatus.ENCRYPTED
                and asset.encrypted_object_public_id is not None
            ):
                public_id = asset.encrypted_object_public_id
                resource_type = "raw"
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
            self._audit(
                "media.deleted",
                principal.user_id,
                media_id,
                status=asset.status,
            )

    def _validate_intent(self, intent: UploadIntent) -> _FormatPolicy:
        expected_confidentiality = (
            MediaConfidentiality.PUBLIC
            if intent.purpose is MediaPurpose.PUBLIC_WORK
            else MediaConfidentiality.PRIVATE
        )
        if intent.confidentiality is not expected_confidentiality:
            raise MediaValidationError(
                "Confidentiality does not match the requested purpose."
            )
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
        suffixes = [suffix.lower() for suffix in PurePath(intent.filename).suffixes]
        if not suffixes or suffixes[-1] not in policy.extensions:
            raise MediaValidationError("Filename extension does not match MIME type.")
        if any(suffix in _DANGEROUS_INNER_EXTENSIONS for suffix in suffixes[:-1]):
            raise MediaValidationError("Filename is not allowed.")
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
            inspection_attempts=asset.inspection_attempts,
            inspection_reason_code=asset.inspection_reason_code,
            inspected_at=asset.inspected_at,
        )

    def _audit(
        self,
        action: str,
        user_id: UUID,
        media_id: UUID,
        *,
        status: MediaStatus,
    ) -> None:
        self._audit_service.record(
            actor_user_id=user_id,
            action=action,
            resource_type="media_asset",
            resource_id=str(media_id),
            after={"status": status.value},
        )

    async def close(self) -> None:
        await self._gateway.close()
        await self._session.close()
