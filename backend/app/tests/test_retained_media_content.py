import asyncio
import hashlib
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.media.encryption import DocumentEncryptionKeyring
from app.modules.media.errors import MediaInvalidStateError
from app.modules.media.models import MediaAsset, MediaEncryptionStatus
from app.modules.media.retained_content import read_retained_content


@pytest.mark.parametrize("corrupt", [False, True])
def test_legacy_retained_content_decrypts_and_rejects_corruption(corrupt: bool) -> None:
    content = b"retained video bytes"
    media_id = uuid4()
    digest = hashlib.sha256(content).hexdigest()
    keyring = DocumentEncryptionKeyring(
        active_key_id="legacy", keys={"legacy": b"k" * 32}
    )
    encrypted = keyring.encrypt(content, media_id=media_id, sha256=digest)
    asset = MediaAsset(
        id=media_id,
        bytes=len(content),
        sha256=digest,
        encryption_status=MediaEncryptionStatus.ENCRYPTED,
        encryption_key_id=encrypted.key_id,
        encryption_nonce=encrypted.nonce,
        encryption_tag=encrypted.tag,
        encrypted_object_public_id="protected/legacy",
        encrypted_bytes=len(encrypted.ciphertext),
    )
    gateway = AsyncMock()
    ciphertext = encrypted.ciphertext
    gateway.download_asset.return_value = (
        bytes([ciphertext[0] ^ 1]) + ciphertext[1:] if corrupt else ciphertext
    )
    if corrupt:
        with pytest.raises(MediaInvalidStateError):
            asyncio.run(read_retained_content(asset, gateway, keyring))
    else:
        assert asyncio.run(read_retained_content(asset, gateway, keyring)) == content
    gateway.download_asset.assert_awaited_once_with(
        public_id="protected/legacy",
        resource_type="raw",
        file_format="bin",
        max_bytes=len(ciphertext),
    )


def test_legacy_content_rejects_unbounded_metadata_before_download() -> None:
    asset = MediaAsset(bytes=301 * 1024 * 1024)
    gateway = AsyncMock()
    with pytest.raises(MediaInvalidStateError):
        asyncio.run(read_retained_content(asset, gateway, None))
    gateway.download_asset.assert_not_awaited()
