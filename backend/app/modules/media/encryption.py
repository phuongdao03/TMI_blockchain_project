import base64
import binascii
import os
import re
from dataclasses import dataclass
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class DocumentEncryptionConfigurationError(RuntimeError):
    """Raised when document encryption key material is unsafe or incomplete."""


@dataclass(frozen=True, slots=True)
class EncryptedDocument:
    key_id: str
    nonce: bytes
    ciphertext: bytes
    tag: bytes


class DocumentEncryptionKeyring:
    _NONCE_BYTES = 12
    _KEY_BYTES = 32
    _KEY_ID = re.compile(r"[A-Za-z0-9_.-]{1,64}")

    def __init__(self, *, active_key_id: str, keys: dict[str, bytes]) -> None:
        if self._KEY_ID.fullmatch(active_key_id) is None or active_key_id not in keys:
            raise DocumentEncryptionConfigurationError(
                "The active document encryption key is not available."
            )
        if not keys or any(
            self._KEY_ID.fullmatch(key_id) is None or len(key) != self._KEY_BYTES
            for key_id, key in keys.items()
        ):
            raise DocumentEncryptionConfigurationError(
                "Document encryption keys must be named 32-byte keys."
            )
        self._active_key_id = active_key_id
        self._keys = dict(keys)

    @classmethod
    def from_base64_keys(
        cls,
        *,
        active_key_id: str,
        encoded_keys: dict[str, str],
    ) -> "DocumentEncryptionKeyring":
        try:
            keys = {
                key_id: base64.b64decode(value, validate=True)
                for key_id, value in encoded_keys.items()
            }
        except (binascii.Error, ValueError) as exc:
            raise DocumentEncryptionConfigurationError(
                "Document encryption keys must be valid base64."
            ) from exc
        return cls(active_key_id=active_key_id, keys=keys)

    @staticmethod
    def _associated_data(media_id: UUID, sha256: str) -> bytes:
        if re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise ValueError("Trusted SHA-256 must be lowercase hexadecimal.")
        return f"tmi-media-v1:{media_id}:{sha256}".encode("ascii")

    def encrypt(
        self,
        plaintext: bytes,
        *,
        media_id: UUID,
        sha256: str,
    ) -> EncryptedDocument:
        nonce = os.urandom(self._NONCE_BYTES)
        combined = AESGCM(self._keys[self._active_key_id]).encrypt(
            nonce,
            plaintext,
            self._associated_data(media_id, sha256),
        )
        return EncryptedDocument(
            key_id=self._active_key_id,
            nonce=nonce,
            ciphertext=combined[:-16],
            tag=combined[-16:],
        )

    def decrypt(
        self,
        document: EncryptedDocument,
        *,
        media_id: UUID,
        sha256: str,
    ) -> bytes:
        key = self._keys.get(document.key_id)
        if key is None:
            raise DocumentEncryptionConfigurationError(
                "The document encryption key is unavailable."
            )
        return AESGCM(key).decrypt(
            document.nonce,
            document.ciphertext + document.tag,
            self._associated_data(media_id, sha256),
        )
