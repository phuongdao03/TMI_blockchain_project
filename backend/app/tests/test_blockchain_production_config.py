import base64

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.blockchain.gateway import SUPPORTED_CHAINS

CONTRACT = "0x" + "11" * 20


def _production(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "firebase_totp_enabled": True,
        "audit_integrity_key": "audit-integrity-test-key-32-bytes",
        "media_private_encryption_enabled": True,
        "media_private_encryption_active_key_id": "document-v1",
        "media_private_encryption_keys": {
            "document-v1": base64.b64encode(b"d" * 32).decode("ascii")
        },
        "blockchain_network": "polygon",
        "blockchain_chain_id": 137,
        "blockchain_rpc_url": "https://polygon-rpc.example",
        "certificate_contract_address": CONTRACT,
        "blockchain_allowed_contract_addresses": CONTRACT,
        "blockchain_signer_mode": "human",
        "blockchain_signing_enabled": True,
        "blockchain_signer_private_key": None,
        "payment_provider": "payos",
        "payos_client_id": "client",
        "payos_api_key": "api-key",
        "payos_checksum_key": "checksum",
        "payos_return_url": "https://app.example/payments/return",
        "payos_cancel_url": "https://app.example/payments/cancel",
        "cloudinary_cloud_name": "tmi-production",
        "cloudinary_api_key": "cloudinary-api-key",
        "cloudinary_api_secret": "cloudinary-api-secret",
    }
    values.update(overrides)
    return Settings.model_validate(values)


def test_production_blockchain_configuration_is_accepted() -> None:
    settings = _production(
        blockchain_explorer_base_url="https://polygonscan.com",
    )
    assert settings.blockchain_network == "polygon"
    assert settings.blockchain_chain_id == 137
    assert SUPPORTED_CHAINS[settings.blockchain_network] == settings.blockchain_chain_id


def test_production_requires_firebase_totp_attestation() -> None:
    with pytest.raises(ValidationError):
        _production(firebase_totp_enabled=False)


def test_production_requires_a_dedicated_audit_integrity_key() -> None:
    with pytest.raises(ValidationError, match="audit integrity key"):
        _production(audit_integrity_key=None)


def test_production_requires_valid_private_document_encryption() -> None:
    with pytest.raises(ValidationError, match="document encryption"):
        _production(media_private_encryption_enabled=False)
    with pytest.raises(ValidationError, match="32 bytes"):
        _production(
            media_private_encryption_keys={
                "document-v1": base64.b64encode(b"short").decode("ascii")
            }
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"cloudinary_cloud_name": ""},
        {"cloudinary_api_key": ""},
        {"cloudinary_api_secret": None},
    ],
)
def test_production_requires_cloudinary_credentials_for_upload_signatures(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="Cloudinary"):
        _production(**overrides)


@pytest.mark.parametrize(
    "overrides",
    [
        {"blockchain_network": "amoy", "blockchain_chain_id": 80_002},
        {"blockchain_rpc_url": "http://polygon-rpc.example"},
        {"blockchain_allowed_contract_addresses": "0x" + "33" * 20},
        {"blockchain_signer_mode": "local"},
        {"blockchain_signer_mode": "managed"},
        {"blockchain_signing_enabled": False},
        {"blockchain_explorer_base_url": "http://polygonscan.com"},
        {"blockchain_explorer_base_url": "javascript:alert(1)"},
        {"blockchain_explorer_base_url": "https://user@polygonscan.com"},
    ],
)
def test_production_blockchain_configuration_rejects_unsafe_values(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _production(**overrides)


def test_local_configuration_keeps_anvil_defaults() -> None:
    settings = Settings.model_validate({"app_env": "local"})
    assert settings.blockchain_network == "local"
    assert settings.blockchain_chain_id == 31_337


def test_local_explorer_allows_only_loopback_http() -> None:
    settings = Settings.model_validate(
        {
            "app_env": "local",
            "blockchain_explorer_base_url": "http://localhost:4000",
        }
    )
    assert settings.blockchain_explorer_base_url == "http://localhost:4000"
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "app_env": "local",
                "blockchain_explorer_base_url": "http://explorer.example",
            }
        )
