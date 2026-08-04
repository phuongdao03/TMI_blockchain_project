import base64
import binascii
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SensitiveFieldEncryptionError(RuntimeError):
    """Raised for missing, malformed, or incompatible field encryption."""


class SensitiveFieldCipher:
    _VERSION = b"\x01"
    _NONCE_BYTES = 12

    def __init__(self, *, key: bytes) -> None:
        if len(key) != 32:
            raise SensitiveFieldEncryptionError(
                "PII_ENCRYPTION_KEY must decode to exactly 32 bytes."
            )
        self._cipher = AESGCM(key)

    @classmethod
    def from_base64(cls, encoded_key: str) -> "SensitiveFieldCipher":
        try:
            key = base64.b64decode(encoded_key, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise SensitiveFieldEncryptionError(
                "PII_ENCRYPTION_KEY must be valid base64."
            ) from exc
        return cls(key=key)

    def encrypt(self, value: str) -> bytes:
        nonce = os.urandom(self._NONCE_BYTES)
        ciphertext = self._cipher.encrypt(nonce, value.encode(), None)
        return self._VERSION + nonce + ciphertext

    def decrypt(self, encrypted: bytes) -> str:
        minimum_length = 1 + self._NONCE_BYTES + 16
        if len(encrypted) < minimum_length or encrypted[:1] != self._VERSION:
            raise SensitiveFieldEncryptionError(
                "Encrypted field payload is malformed or unsupported."
            )
        nonce = encrypted[1 : 1 + self._NONCE_BYTES]
        ciphertext = encrypted[1 + self._NONCE_BYTES :]
        return self._cipher.decrypt(nonce, ciphertext, None).decode()
