import asyncio
import base64
import binascii
import hashlib
import json
import os
from dataclasses import dataclass
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class OutboxEncryptionConfigurationError(RuntimeError):
    """Raised when the outbox encryption key is absent or malformed."""


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(type=Type.ID)

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._hasher.hash, password)

    async def verify(self, password_hash: str, password: str) -> bool:
        try:
            return await asyncio.to_thread(
                self._hasher.verify,
                password_hash,
                password,
            )
        except (InvalidHashError, VerifyMismatchError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)


@dataclass(frozen=True, slots=True)
class EncryptedPayload:
    nonce: bytes
    ciphertext: bytes
    key_id: str


class OutboxPayloadCipher:
    def __init__(self, *, key: bytes, key_id: str) -> None:
        if len(key) != 32:
            raise OutboxEncryptionConfigurationError(
                "AUTH_OUTBOX_ENCRYPTION_KEY must decode to exactly 32 bytes."
            )
        if not key_id:
            raise OutboxEncryptionConfigurationError(
                "AUTH_OUTBOX_KEY_ID must not be empty."
            )
        self._cipher = AESGCM(key)
        self._key_id = key_id

    @classmethod
    def from_base64(cls, *, encoded_key: str, key_id: str) -> "OutboxPayloadCipher":
        try:
            key = base64.b64decode(encoded_key, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise OutboxEncryptionConfigurationError(
                "AUTH_OUTBOX_ENCRYPTION_KEY must be valid base64."
            ) from exc
        return cls(key=key, key_id=key_id)

    @staticmethod
    def _associated_data(event_type: str, aggregate_id: UUID) -> bytes:
        return f"{event_type}:{aggregate_id}".encode()

    def encrypt(
        self,
        payload: dict[str, str],
        *,
        event_type: str,
        aggregate_id: UUID,
    ) -> EncryptedPayload:
        nonce = os.urandom(12)
        plaintext = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        ciphertext = self._cipher.encrypt(
            nonce,
            plaintext,
            self._associated_data(event_type, aggregate_id),
        )
        return EncryptedPayload(
            nonce=nonce,
            ciphertext=ciphertext,
            key_id=self._key_id,
        )

    def decrypt(
        self,
        *,
        nonce: bytes,
        ciphertext: bytes,
        event_type: str,
        aggregate_id: UUID,
    ) -> str:
        plaintext = self._cipher.decrypt(
            nonce,
            ciphertext,
            self._associated_data(event_type, aggregate_id),
        )
        return plaintext.decode()


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
