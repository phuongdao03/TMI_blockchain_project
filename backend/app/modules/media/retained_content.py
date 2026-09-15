import hashlib
from typing import Protocol

from cryptography.exceptions import InvalidTag

from app.modules.media.encryption import (
    DocumentEncryptionConfigurationError,
    DocumentEncryptionKeyring,
    EncryptedDocument,
)
from app.modules.media.errors import MediaInvalidStateError
from app.modules.media.models import MediaAsset, MediaEncryptionStatus


class RetainedDownloadGateway(Protocol):
    async def download_asset(
        self, *, public_id: str, resource_type: str, file_format: str, max_bytes: int
    ) -> bytes: ...


async def read_retained_content(
    asset: MediaAsset,
    gateway: RetainedDownloadGateway,
    keyring: DocumentEncryptionKeyring | None,
) -> bytes:
    # Bound legacy decryption memory even if stored metadata is malformed.
    if asset.bytes <= 0 or asset.bytes > 300 * 1024 * 1024:
        raise MediaInvalidStateError()
    if asset.encryption_status is MediaEncryptionStatus.ENCRYPTED:
        if (
            keyring is None
            or asset.sha256 is None
            or asset.encryption_key_id is None
            or asset.encryption_nonce is None
            or asset.encryption_tag is None
            or asset.encrypted_object_public_id is None
            or asset.encrypted_bytes is None
            or asset.encrypted_bytes <= 0
            or asset.encrypted_bytes > 300 * 1024 * 1024
        ):
            raise MediaInvalidStateError()
        ciphertext = await gateway.download_asset(
            public_id=asset.encrypted_object_public_id,
            resource_type="raw",
            file_format="bin",
            max_bytes=asset.encrypted_bytes,
        )
        if len(ciphertext) != asset.encrypted_bytes:
            raise MediaInvalidStateError()
        try:
            content = keyring.decrypt(
                EncryptedDocument(
                    key_id=asset.encryption_key_id,
                    nonce=asset.encryption_nonce,
                    ciphertext=ciphertext,
                    tag=asset.encryption_tag,
                ),
                media_id=asset.id,
                sha256=asset.sha256,
            )
        except (InvalidTag, ValueError, DocumentEncryptionConfigurationError):
            raise MediaInvalidStateError() from None
    else:
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
        if file_format is None:
            raise MediaInvalidStateError()
        content = await gateway.download_asset(
            public_id=asset.cloudinary_public_id,
            resource_type=asset.resource_type,
            file_format=file_format,
            max_bytes=asset.bytes,
        )
        if len(content) != asset.bytes:
            raise MediaInvalidStateError()
    if (
        len(content) != asset.bytes
        or asset.sha256 is None
        or hashlib.sha256(content).hexdigest() != asset.sha256
    ):
        raise MediaInvalidStateError()
    return content
