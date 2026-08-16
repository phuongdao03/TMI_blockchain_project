import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_application


def preview_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "release_mode": "preview",
        "app_base_url": "https://preview.example.com",
        "cors_allowed_origins": "https://preview.example.com",
        "firebase_project_id": "tmi-preview",
        "audit_integrity_key": "audit-integrity-test-key-32-bytes",
        "payment_provider": "disabled",
        "media_private_encryption_enabled": False,
        "firebase_totp_enabled": False,
    }
    values.update(overrides)
    return Settings.model_validate(values)


def test_production_preview_does_not_require_payment_or_blockchain_credentials() -> (
    None
):
    settings = preview_settings()

    assert settings.release_mode == "preview"
    assert settings.payment_provider == "disabled"
    assert settings.business_workflows_enabled is False


def test_production_preview_still_rejects_raw_blockchain_private_keys() -> None:
    with pytest.raises(ValidationError, match="Raw blockchain signer keys"):
        preview_settings(blockchain_signer_private_key="0x" + "11" * 32)


def test_preview_denies_business_mutations_but_not_auth_contracts() -> None:
    app = create_application(settings=preview_settings())
    client = TestClient(app, raise_server_exceptions=False)

    denied = client.post("/api/v1/dossiers", json={})
    auth_contract = client.post("/api/v1/auth/firebase/exchange", json={})

    assert denied.status_code == 503
    assert denied.json()["error"]["code"] == "FEATURE_NOT_AVAILABLE"
    assert auth_contract.status_code != 503


def test_production_preview_does_not_publish_api_documentation() -> None:
    client = TestClient(
        create_application(settings=preview_settings()),
        raise_server_exceptions=False,
    )

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_full_production_keeps_provider_requirements() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "app_env": "production",
                "release_mode": "full",
                "firebase_project_id": "tmi-production",
                "audit_integrity_key": "audit-integrity-test-key-32-bytes",
            }
        )
