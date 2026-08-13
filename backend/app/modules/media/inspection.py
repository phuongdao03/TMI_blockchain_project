import asyncio
import hashlib
import struct
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from typing import Protocol
from uuid import UUID

from cryptography.exceptions import InvalidTag
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.dossiers.similarity import SimilarityInputError, image_dhash
from app.modules.media.encryption import (
    DocumentEncryptionConfigurationError,
    DocumentEncryptionKeyring,
    EncryptedDocument,
)
from app.modules.media.errors import MediaProviderUnavailableError
from app.modules.media.gateway import (
    MediaContentTooLargeError,
    ProviderAssetMetadata,
    StoredEncryptedAsset,
)
from app.modules.media.models import (
    MediaAsset,
    MediaConfidentiality,
    MediaEncryptionStatus,
    MediaStatus,
)
from app.modules.media.provenance import (
    CURRENT_INSPECTION_POLICY_VERSION,
    HASH_ALGORITHM,
)
from app.modules.media.repository import MediaAssetRepository

_ACTIVE_PDF_TOKENS = (
    b"/AA",
    b"/AcroForm",
    b"/EmbeddedFile",
    b"/JavaScript",
    b"/JS",
    b"/Launch",
    b"/OpenAction",
    b"/RichMedia",
    b"/SubmitForm",
    b"/XFA",
)
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
_DELIVERY_FORMATS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
    "audio/mpeg": "mp3",
    "audio/mp4": "mp4",
    "audio/ogg": "ogg",
    "video/mp4": "mp4",
    "video/webm": "webm",
}


class InspectionRejectedError(Exception):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class InspectionUnavailableError(Exception):
    def __init__(self, reason_code: str = "SCANNER_UNAVAILABLE") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True, slots=True)
class MalwareScanResult:
    is_clean: bool
    signature: str | None = None

    @classmethod
    def clean(cls) -> "MalwareScanResult":
        return cls(is_clean=True)

    @classmethod
    def infected(cls, signature: str) -> "MalwareScanResult":
        return cls(is_clean=False, signature=signature)


class MediaContentGateway(Protocol):
    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> ProviderAssetMetadata: ...

    async def download_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        max_bytes: int,
    ) -> bytes: ...

    async def upload_encrypted_asset(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredEncryptedAsset: ...

    async def delete_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> None: ...


class MalwareScanner(Protocol):
    async def scan(self, content: bytes) -> MalwareScanResult: ...


class MediaInspectionPolicy:
    def validate(self, filename: str, mime_type: str, content: bytes) -> None:
        self._validate_filename(filename)
        if not content:
            raise InspectionRejectedError("EMPTY_FILE")
        validator = {
            "image/jpeg": self._jpeg,
            "image/png": self._png,
            "image/webp": self._webp,
            "application/pdf": self._pdf,
            "audio/mpeg": self._mpeg_audio,
            "audio/mp4": self._mp4,
            "audio/ogg": self._ogg,
            "video/mp4": self._mp4,
            "video/webm": self._webm,
        }.get(mime_type)
        if validator is None or not validator(content):
            raise InspectionRejectedError("MAGIC_BYTES_MISMATCH")

    @staticmethod
    def _validate_filename(filename: str) -> None:
        suffixes = [suffix.lower() for suffix in PurePath(filename).suffixes]
        if any(suffix in _DANGEROUS_INNER_EXTENSIONS for suffix in suffixes[:-1]):
            raise InspectionRejectedError("SUSPICIOUS_FILENAME")

    @staticmethod
    def _jpeg(content: bytes) -> bool:
        return content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9")

    @staticmethod
    def _png(content: bytes) -> bool:
        return content.startswith(b"\x89PNG\r\n\x1a\n")

    @staticmethod
    def _webp(content: bytes) -> bool:
        return (
            len(content) >= 12
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        )

    @staticmethod
    def _pdf(content: bytes) -> bool:
        if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-1_024:]:
            raise InspectionRejectedError("PDF_MALFORMED")
        if any(token in content for token in _ACTIVE_PDF_TOKENS):
            raise InspectionRejectedError("PDF_ACTIVE_CONTENT")
        return True

    @staticmethod
    def _mpeg_audio(content: bytes) -> bool:
        return content.startswith(b"ID3") or (
            len(content) >= 2 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0
        )

    @staticmethod
    def _mp4(content: bytes) -> bool:
        return len(content) >= 12 and content[4:8] == b"ftyp"

    @staticmethod
    def _ogg(content: bytes) -> bool:
        return content.startswith(b"OggS")

    @staticmethod
    def _webm(content: bytes) -> bool:
        return content.startswith(b"\x1aE\xdf\xa3")


class ClamAvScanner:
    def __init__(self, *, host: str, port: int, timeout_seconds: float) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds

    async def scan(self, content: bytes) -> MalwareScanResult:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                reader, writer = await asyncio.open_connection(self._host, self._port)
                try:
                    writer.write(b"zINSTREAM\0")
                    for offset in range(0, len(content), 64 * 1_024):
                        chunk = content[offset : offset + 64 * 1_024]
                        writer.write(struct.pack("!I", len(chunk)))
                        writer.write(chunk)
                    writer.write(struct.pack("!I", 0))
                    await writer.drain()
                    response = await reader.readuntil(b"\0")
                finally:
                    writer.close()
                    await writer.wait_closed()
        except (OSError, TimeoutError, asyncio.IncompleteReadError) as exc:
            raise InspectionUnavailableError() from exc
        result = response.rstrip(b"\0").decode("utf-8", errors="replace")
        if result.endswith(" OK"):
            return MalwareScanResult.clean()
        if result.endswith(" FOUND"):
            signature = result.rsplit(": ", maxsplit=1)[-1].removesuffix(" FOUND")
            return MalwareScanResult.infected(signature[:128])
        raise InspectionUnavailableError("SCANNER_PROTOCOL_ERROR")


class MediaInspectionService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: MediaContentGateway,
        scanner: MalwareScanner,
        max_attempts: int,
        encryption_keyring: DocumentEncryptionKeyring | None = None,
        private_encryption_required: bool = False,
        policy: MediaInspectionPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = MediaAssetRepository(session)
        self._audit_service = AuditService(session)
        self._gateway = gateway
        self._scanner = scanner
        self._max_attempts = max_attempts
        self._encryption_keyring = encryption_keyring
        self._private_encryption_required = private_encryption_required
        self._policy = policy or MediaInspectionPolicy()
        self._clock = clock or (lambda: datetime.now(UTC))

    async def inspect(self, media_id: UUID) -> None:
        async with self._session.begin():
            asset = await self._repository.get_by_id(media_id, for_update=True)
            if asset is None:
                return
            if asset.status in {MediaStatus.ACTIVE, MediaStatus.REJECTED}:
                return
            if asset.status is not MediaStatus.QUARANTINED:
                raise InspectionRejectedError("INVALID_INSPECTION_STATE")
            snapshot = (
                asset.cloudinary_public_id,
                asset.resource_type,
                asset.original_filename,
                asset.mime_type,
                asset.bytes,
                asset.confidentiality,
                asset.encryption_status,
            )

        (
            public_id,
            resource_type,
            filename,
            mime_type,
            expected_bytes,
            confidentiality,
            encryption_status,
        ) = snapshot
        if (
            confidentiality is MediaConfidentiality.PRIVATE
            and self._private_encryption_required
            and encryption_status is MediaEncryptionStatus.ENCRYPTED
        ):
            await self._delete_plaintext_and_activate(
                media_id,
                staging_public_id=public_id,
                staging_resource_type=resource_type,
            )
            return
        try:
            content = await self._gateway.download_asset(
                public_id=public_id,
                resource_type=resource_type,
                file_format=_DELIVERY_FORMATS[mime_type],
                max_bytes=expected_bytes,
            )
            if len(content) != expected_bytes:
                raise InspectionRejectedError("SIZE_MISMATCH")
            self._policy.validate(filename, mime_type, content)
            perceptual_hash = self._perceptual_hash(mime_type, content)
            scan = await self._scanner.scan(content)
            if not scan.is_clean:
                raise InspectionRejectedError("MALWARE_DETECTED")
        except MediaContentTooLargeError:
            await self._record(
                media_id,
                rejected=True,
                reason_code="SIZE_LIMIT_EXCEEDED",
            )
            return
        except InspectionRejectedError as exc:
            await self._record(media_id, rejected=True, reason_code=exc.reason_code)
            return
        except MediaProviderUnavailableError as provider_exc:
            unavailable = InspectionUnavailableError("PROVIDER_UNAVAILABLE")
            exhausted = await self._record(
                media_id,
                rejected=False,
                reason_code=unavailable.reason_code,
            )
            if not exhausted:
                raise unavailable from provider_exc
            return
        except InspectionUnavailableError as exc:
            exhausted = await self._record(
                media_id,
                rejected=False,
                reason_code=exc.reason_code,
            )
            if not exhausted:
                raise
            return

        digest = hashlib.sha256(content).hexdigest()
        if (
            confidentiality is MediaConfidentiality.PRIVATE
            and self._private_encryption_required
        ):
            await self._encrypt_private(
                media_id,
                content=content,
                digest=digest,
                perceptual_hash=perceptual_hash,
                staging_public_id=public_id,
                staging_resource_type=resource_type,
            )
            return
        async with self._session.begin():
            asset = await self._repository.get_by_id(media_id, for_update=True)
            if asset is None or asset.status is not MediaStatus.QUARANTINED:
                return
            asset.inspection_attempts += 1
            asset.inspection_reason_code = None
            asset.inspected_at = self._clock()
            asset.sha256 = digest
            asset.status = MediaStatus.ACTIVE
            asset.encryption_status = (
                MediaEncryptionStatus.NOT_REQUIRED
                if asset.confidentiality is MediaConfidentiality.PUBLIC
                else MediaEncryptionStatus.LEGACY_UNENCRYPTED
            )
            self._set_provenance(
                asset,
                digest=digest,
                perceptual_hash=perceptual_hash,
            )
            self._audit(asset, "CLEAN")

    async def _encrypt_private(
        self,
        media_id: UUID,
        *,
        content: bytes,
        digest: str,
        perceptual_hash: str | None,
        staging_public_id: str,
        staging_resource_type: str,
    ) -> None:
        if self._encryption_keyring is None:
            unavailable = InspectionUnavailableError("ENCRYPTION_KEY_UNAVAILABLE")
            exhausted = await self._record(
                media_id,
                rejected=False,
                reason_code=unavailable.reason_code,
            )
            if not exhausted:
                raise unavailable
            return
        encrypted = self._encryption_keyring.encrypt(
            content,
            media_id=media_id,
            sha256=digest,
        )
        encrypted_public_id = f"{staging_public_id}-ciphertext"
        try:
            stored = await self._gateway.upload_encrypted_asset(
                public_id=encrypted_public_id,
                content=encrypted.ciphertext,
            )
        except MediaProviderUnavailableError as exc:
            unavailable = InspectionUnavailableError("ENCRYPTED_UPLOAD_UNAVAILABLE")
            exhausted = await self._record(
                media_id,
                rejected=False,
                reason_code=unavailable.reason_code,
            )
            if not exhausted:
                raise unavailable from exc
            return

        async with self._session.begin():
            asset = await self._repository.get_by_id(media_id, for_update=True)
            if asset is None or asset.status is not MediaStatus.QUARANTINED:
                return
            asset.sha256 = digest
            asset.encryption_status = MediaEncryptionStatus.ENCRYPTED
            asset.encryption_algorithm = "AES-256-GCM"
            asset.encryption_key_id = encrypted.key_id
            asset.encryption_nonce = encrypted.nonce
            asset.encryption_tag = encrypted.tag
            asset.encrypted_object_public_id = stored.public_id
            asset.encrypted_object_version = stored.version
            asset.encrypted_bytes = stored.bytes
            asset.encrypted_at = self._clock()
            self._set_provenance(
                asset,
                digest=digest,
                perceptual_hash=perceptual_hash,
            )

        await self._delete_plaintext_and_activate(
            media_id,
            staging_public_id=staging_public_id,
            staging_resource_type=staging_resource_type,
        )

    async def _delete_plaintext_and_activate(
        self,
        media_id: UUID,
        *,
        staging_public_id: str,
        staging_resource_type: str,
    ) -> None:
        try:
            await self._gateway.delete_asset(
                public_id=staging_public_id,
                resource_type=staging_resource_type,
            )
        except MediaProviderUnavailableError as exc:
            unavailable = InspectionUnavailableError("PLAINTEXT_DELETE_UNAVAILABLE")
            exhausted = await self._record(
                media_id,
                rejected=False,
                reason_code=unavailable.reason_code,
            )
            if not exhausted:
                raise unavailable from exc
            return

        async with self._session.begin():
            asset = await self._repository.get_by_id(media_id, for_update=True)
            if asset is None or asset.status is not MediaStatus.QUARANTINED:
                return
            asset.inspection_attempts += 1
            asset.inspection_reason_code = None
            asset.inspected_at = self._clock()
            asset.status = MediaStatus.ACTIVE
            self._audit(asset, "CLEAN_ENCRYPTED")

    async def reverify(self, media_id: UUID) -> None:
        encrypted_asset: MediaAsset | None = None
        async with self._session.begin():
            asset = await self._repository.get_by_id(media_id, for_update=True)
            if asset is None:
                return
            if asset.status is not MediaStatus.ACTIVE:
                raise InspectionRejectedError("INVALID_REVERIFICATION_STATE")
            if asset.encryption_status is MediaEncryptionStatus.ENCRYPTED:
                encrypted_asset = asset
                snapshot = None
            else:
                snapshot = (
                    asset.cloudinary_public_id,
                    asset.resource_type,
                    asset.original_filename,
                    asset.mime_type,
                    asset.bytes,
                    asset.sha256,
                )

        if encrypted_asset is not None:
            await self._reverify_encrypted(encrypted_asset)
            return
        assert snapshot is not None

        public_id, resource_type, filename, mime_type, expected_bytes, trusted_hash = (
            snapshot
        )
        metadata = await self._gateway.get_asset_metadata(
            public_id=public_id,
            resource_type=resource_type,
        )
        if (
            metadata.public_id != public_id
            or metadata.resource_type != resource_type
            or metadata.delivery_type != "authenticated"
            or metadata.file_format != _DELIVERY_FORMATS[mime_type]
            or metadata.bytes != expected_bytes
        ):
            await self._reject_active(media_id, "STORAGE_METADATA_MISMATCH")
            return
        try:
            content = await self._gateway.download_asset(
                public_id=public_id,
                resource_type=resource_type,
                file_format=_DELIVERY_FORMATS[mime_type],
                max_bytes=expected_bytes,
            )
            if len(content) != expected_bytes:
                raise InspectionRejectedError("SIZE_MISMATCH")
            self._policy.validate(filename, mime_type, content)
            perceptual_hash = self._perceptual_hash(mime_type, content)
            scan = await self._scanner.scan(content)
            if not scan.is_clean:
                raise InspectionRejectedError("MALWARE_DETECTED")
        except MediaContentTooLargeError:
            await self._reject_active(media_id, "SIZE_LIMIT_EXCEEDED")
            return
        except InspectionRejectedError as exc:
            await self._reject_active(media_id, exc.reason_code)
            return

        digest = hashlib.sha256(content).hexdigest()
        if trusted_hash is not None and digest != trusted_hash:
            await self._reject_active(media_id, "HASH_MISMATCH")
            return
        async with self._session.begin():
            asset = await self._repository.get_by_id(media_id, for_update=True)
            if asset is None or asset.status is not MediaStatus.ACTIVE:
                return
            if asset.sha256 is not None and asset.sha256 != digest:
                asset.status = MediaStatus.REJECTED
                asset.inspection_reason_code = "HASH_MISMATCH"
                asset.inspected_at = self._clock()
                self._audit(asset, "HASH_MISMATCH")
                return
            asset.sha256 = digest
            asset.cloudinary_version = metadata.version
            asset.inspection_reason_code = None
            asset.inspected_at = self._clock()
            self._set_provenance(
                asset,
                digest=digest,
                perceptual_hash=perceptual_hash,
            )
            self._audit(asset, "PROVENANCE_REVERIFIED")

    async def _reverify_encrypted(self, asset: MediaAsset) -> None:
        if self._encryption_keyring is None:
            raise InspectionUnavailableError("ENCRYPTION_KEY_UNAVAILABLE")
        if (
            asset.sha256 is None
            or asset.encryption_key_id is None
            or asset.encryption_nonce is None
            or asset.encryption_tag is None
            or asset.encrypted_object_public_id is None
            or asset.encrypted_bytes is None
        ):
            raise InspectionUnavailableError("ENCRYPTION_KEY_UNAVAILABLE")
        snapshot = (
            asset.id,
            asset.sha256,
            asset.encryption_key_id,
            asset.encryption_nonce,
            asset.encryption_tag,
            asset.encrypted_object_public_id,
            asset.encrypted_bytes,
            asset.original_filename,
            asset.mime_type,
            asset.bytes,
        )
        (
            media_id,
            trusted_hash,
            key_id,
            nonce,
            tag,
            public_id,
            encrypted_bytes,
            filename,
            mime_type,
            expected_bytes,
        ) = snapshot
        try:
            ciphertext = await self._gateway.download_asset(
                public_id=public_id,
                resource_type="raw",
                file_format="bin",
                max_bytes=encrypted_bytes,
            )
        except MediaContentTooLargeError:
            await self._reject_active(media_id, "ENCRYPTED_SIZE_MISMATCH")
            return
        try:
            content = self._encryption_keyring.decrypt(
                EncryptedDocument(
                    key_id=key_id,
                    nonce=nonce,
                    ciphertext=ciphertext,
                    tag=tag,
                ),
                media_id=media_id,
                sha256=trusted_hash,
            )
        except (InvalidTag, DocumentEncryptionConfigurationError):
            await self._reject_active(media_id, "ENCRYPTED_CONTENT_INVALID")
            return
        if len(content) != expected_bytes:
            await self._reject_active(media_id, "SIZE_MISMATCH")
            return
        try:
            self._policy.validate(filename, mime_type, content)
            perceptual_hash = self._perceptual_hash(mime_type, content)
            scan = await self._scanner.scan(content)
            if not scan.is_clean:
                raise InspectionRejectedError("MALWARE_DETECTED")
        except InspectionRejectedError as exc:
            await self._reject_active(media_id, exc.reason_code)
            return
        digest = hashlib.sha256(content).hexdigest()
        if digest != trusted_hash:
            await self._reject_active(media_id, "HASH_MISMATCH")
            return
        async with self._session.begin():
            current = await self._repository.get_by_id(media_id, for_update=True)
            if current is None or current.status is not MediaStatus.ACTIVE:
                return
            current.inspection_reason_code = None
            current.inspected_at = self._clock()
            self._set_provenance(
                current,
                digest=digest,
                perceptual_hash=perceptual_hash,
            )
            self._audit(current, "ENCRYPTED_PROVENANCE_REVERIFIED")

    async def _reject_active(self, media_id: UUID, reason_code: str) -> None:
        async with self._session.begin():
            asset = await self._repository.get_by_id(media_id, for_update=True)
            if asset is None or asset.status is not MediaStatus.ACTIVE:
                return
            asset.status = MediaStatus.REJECTED
            asset.inspection_reason_code = reason_code
            asset.inspected_at = self._clock()
            self._audit(asset, reason_code)

    @staticmethod
    def _perceptual_hash(mime_type: str, content: bytes) -> str | None:
        if not mime_type.startswith("image/"):
            return None
        try:
            return image_dhash(content)
        except SimilarityInputError as exc:
            raise InspectionRejectedError("IMAGE_DECODE_FAILED") from exc

    def _set_provenance(
        self,
        asset: MediaAsset,
        *,
        digest: str,
        perceptual_hash: str | None,
    ) -> None:
        asset.sha256 = digest
        asset.perceptual_hash = perceptual_hash
        asset.hash_algorithm = HASH_ALGORITHM
        asset.hash_byte_length = asset.bytes
        asset.inspection_policy_version = CURRENT_INSPECTION_POLICY_VERSION
        asset.hash_storage_version = (
            asset.encrypted_object_version
            if asset.encryption_status is MediaEncryptionStatus.ENCRYPTED
            else asset.cloudinary_version
        )
        asset.hash_computed_at = self._clock()

    async def _record(
        self,
        media_id: UUID,
        *,
        rejected: bool,
        reason_code: str,
    ) -> bool:
        async with self._session.begin():
            asset = await self._repository.get_by_id(media_id, for_update=True)
            if asset is None or asset.status is not MediaStatus.QUARANTINED:
                return True
            asset.inspection_attempts += 1
            exhausted = asset.inspection_attempts >= self._max_attempts
            asset.inspection_reason_code = (
                "INSPECTION_RETRY_EXHAUSTED"
                if exhausted and not rejected
                else reason_code
            )
            if rejected or exhausted:
                asset.status = MediaStatus.REJECTED
                asset.inspected_at = self._clock()
            self._audit(asset, reason_code)
        return rejected or exhausted

    def _audit(self, asset: MediaAsset, result_code: str) -> None:
        self._audit_service.record(
            actor_user_id=None,
            actor_service="media-inspection-worker",
            action="media.inspected",
            resource_type="media_asset",
            resource_id=str(asset.id),
            after={"status": asset.status.value, "result_code": result_code},
        )
