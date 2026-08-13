from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _isolate_settings_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parent)
    for field_name in Settings.model_fields:
        monkeypatch.delenv(field_name.upper(), raising=False)


def test_mock_payment_provider_is_local_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_settings_sources(monkeypatch)
    with pytest.raises(ValidationError, match="local-only"):
        Settings.model_validate(
            {
                "app_env": "staging",
                "payment_provider": "mock",
                "payment_webhook_secret": "secret",
                "payment_checkout_base_url": "https://pay.example.com/checkout",
            }
        )


def test_non_local_payment_requires_payos_credentials_and_https_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_settings_sources(monkeypatch)
    with pytest.raises(ValidationError, match="Client ID"):
        Settings.model_validate(
            {
                "app_env": "staging",
                "payment_provider": "payos",
            }
        )


def test_firebase_emulator_is_rejected_outside_local_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_settings_sources(monkeypatch)
    with pytest.raises(ValidationError, match="Firebase Auth emulator"):
        Settings.model_validate(
            {
                "app_env": "staging",
                "firebase_auth_emulator_host": "firebase-emulator:9099",
                "payment_provider": "payos",
                "payos_client_id": "client",
                "payos_api_key": "api-key",
                "payos_checksum_key": "checksum",
                "payos_return_url": "https://app.example/payments/return",
                "payos_cancel_url": "https://app.example/payments/cancel",
            }
        )

    settings = Settings.model_validate(
        {
            "app_env": "local",
            "firebase_auth_emulator_host": "firebase-emulator:9099",
        }
    )
    assert settings.firebase_auth_emulator_host == "firebase-emulator:9099"

    with pytest.raises(ValidationError, match="HTTPS"):
        Settings.model_validate(
            {
                "app_env": "staging",
                "payment_provider": "payos",
                "payos_client_id": "client",
                "payos_api_key": "api-key",
                "payos_checksum_key": "checksum",
                "payos_return_url": "http://app.example/payments/return",
                "payos_cancel_url": "https://app.example/payments/cancel",
            }
        )


def test_real_money_test_gate_is_bounded_and_never_enabled_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_settings_sources(monkeypatch)
    settings = Settings.model_validate(
        {
            "app_env": "staging",
            "payment_provider": "payos",
            "payos_client_id": "client",
            "payos_api_key": "api-key",
            "payos_checksum_key": "checksum",
            "payos_return_url": "https://app.example/payments/return",
            "payos_cancel_url": "https://app.example/payments/cancel",
            "payment_real_money_test_enabled": True,
            "payment_real_money_test_max_amount_vnd": 5_000,
        }
    )
    assert settings.payment_real_money_test_max_amount_vnd == 5_000

    with pytest.raises(ValidationError, match="cannot be enabled in production"):
        Settings.model_validate(
            {
                "app_env": "production",
                "firebase_totp_enabled": True,
                "audit_integrity_key": "audit-integrity-test-key-32-bytes",
                "media_private_encryption_enabled": True,
                "media_private_encryption_active_key_id": "document-v1",
                "media_private_encryption_keys": {
                    "document-v1": "ZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGRkZGQ="
                },
                "blockchain_network": "polygon",
                "blockchain_chain_id": 137,
                "blockchain_rpc_url": "https://polygon-rpc.example",
                "certificate_contract_address": "0x" + "11" * 20,
                "blockchain_allowed_contract_addresses": "0x" + "11" * 20,
                "blockchain_signer_mode": "managed",
                "blockchain_managed_signer_url": "https://signer.example/v1/sign",
                "blockchain_managed_signer_key_id": "projects/tmi/keys/issuer",
                "blockchain_managed_signer_expected_address": "0x" + "22" * 20,
                "payment_provider": "payos",
                "payos_client_id": "client",
                "payos_api_key": "api-key",
                "payos_checksum_key": "checksum",
                "payos_return_url": "https://app.example/payments/return",
                "payos_cancel_url": "https://app.example/payments/cancel",
                "payment_real_money_test_enabled": True,
            }
        )
