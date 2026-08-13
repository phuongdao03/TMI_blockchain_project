import base64
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag

from app.modules.media.encryption import (
    DocumentEncryptionConfigurationError,
    DocumentEncryptionKeyring,
)


def encoded(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def test_private_document_round_trip_binds_ciphertext_to_media_identity() -> None:
    media_id = uuid4()
    keyring = DocumentEncryptionKeyring.from_base64_keys(
        active_key_id="document-v2",
        encoded_keys={
            "document-v1": encoded(b"1" * 32),
            "document-v2": encoded(b"2" * 32),
        },
    )

    encrypted = keyring.encrypt(
        b"trusted original bytes",
        media_id=media_id,
        sha256="a" * 64,
    )

    assert encrypted.key_id == "document-v2"
    assert len(encrypted.nonce) == 12
    assert len(encrypted.tag) == 16
    assert encrypted.ciphertext != b"trusted original bytes"
    assert (
        keyring.decrypt(
            encrypted,
            media_id=media_id,
            sha256="a" * 64,
        )
        == b"trusted original bytes"
    )


def test_private_document_decryption_rejects_tampered_identity_or_ciphertext() -> None:
    keyring = DocumentEncryptionKeyring.from_base64_keys(
        active_key_id="document-v1",
        encoded_keys={"document-v1": encoded(b"k" * 32)},
    )
    encrypted = keyring.encrypt(
        b"private evidence",
        media_id=uuid4(),
        sha256="b" * 64,
    )

    with pytest.raises(InvalidTag):
        keyring.decrypt(encrypted, media_id=uuid4(), sha256="b" * 64)


def test_private_document_encryption_uses_a_fresh_nonce() -> None:
    media_id = uuid4()
    keyring = DocumentEncryptionKeyring.from_base64_keys(
        active_key_id="document-v1",
        encoded_keys={"document-v1": encoded(b"k" * 32)},
    )

    first = keyring.encrypt(b"same bytes", media_id=media_id, sha256="c" * 64)
    second = keyring.encrypt(b"same bytes", media_id=media_id, sha256="c" * 64)

    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


def test_historical_key_remains_decrypt_only_after_rotation() -> None:
    media_id = uuid4()
    old_keyring = DocumentEncryptionKeyring(
        active_key_id="document-v1",
        keys={"document-v1": b"1" * 32},
    )
    encrypted = old_keyring.encrypt(
        b"historical evidence",
        media_id=media_id,
        sha256="d" * 64,
    )
    rotated_keyring = DocumentEncryptionKeyring(
        active_key_id="document-v2",
        keys={"document-v1": b"1" * 32, "document-v2": b"2" * 32},
    )

    assert (
        rotated_keyring.decrypt(
            encrypted,
            media_id=media_id,
            sha256="d" * 64,
        )
        == b"historical evidence"
    )
    assert (
        rotated_keyring.encrypt(
            b"new evidence",
            media_id=media_id,
            sha256="e" * 64,
        ).key_id
        == "document-v2"
    )


def test_document_keyring_rejects_missing_active_or_invalid_keys() -> None:
    with pytest.raises(DocumentEncryptionConfigurationError):
        DocumentEncryptionKeyring.from_base64_keys(
            active_key_id="missing",
            encoded_keys={"document-v1": encoded(b"k" * 32)},
        )
    with pytest.raises(DocumentEncryptionConfigurationError):
        DocumentEncryptionKeyring.from_base64_keys(
            active_key_id="document-v1",
            encoded_keys={"document-v1": encoded(b"short")},
        )
