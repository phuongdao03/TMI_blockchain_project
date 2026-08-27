import base64
import binascii
import json
import re
from ast import literal_eval
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # Source: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "staging", "production"] = "local"
    release_mode: Literal["preview", "full"] = "full"
    app_base_url: str = Field(
        default="http://localhost:3000",
        min_length=1,
        max_length=2_048,
    )
    cors_allowed_origins: str = Field(
        default="http://localhost:3000",
        min_length=1,
        max_length=4_096,
    )
    service_name: str = "backend"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    redis_url: str = "redis://redis:6379/0"
    anvil_rpc_url: str = "http://anvil:8545"
    database_url: SecretStr | None = None
    database_direct_url: SecretStr | None = None
    database_null_pool: bool = False
    readiness_timeout_seconds: float = Field(default=1.0, gt=0, le=10)
    auth_outbox_encryption_key: SecretStr | None = None
    pii_encryption_key: SecretStr | None = None
    audit_integrity_key: SecretStr | None = None
    audit_integrity_key_id: str = Field(
        default="audit-v1",
        min_length=1,
        max_length=64,
    )
    audit_integrity_verification_keys: dict[str, SecretStr] = Field(
        default_factory=dict
    )
    audit_retention_days: int = Field(default=2_555, ge=365, le=3_650)
    auth_outbox_key_id: str = Field(
        default="auth-registration-v1",
        min_length=1,
        max_length=64,
    )
    auth_verification_ttl_seconds: int = Field(
        default=86_400,
        ge=300,
        le=604_800,
    )
    auth_registration_ip_limit: int = Field(default=20, ge=1, le=1_000)
    auth_registration_email_limit: int = Field(default=5, ge=1, le=1_000)
    auth_registration_rate_window_seconds: int = Field(
        default=900,
        ge=1,
        le=86_400,
    )
    jwt_secret: SecretStr | None = None
    auth_csrf_secret: SecretStr | None = None
    auth_jwt_issuer: str = Field(default="tmi-platform", min_length=1, max_length=128)
    auth_jwt_audience: str = Field(default="tmi-web", min_length=1, max_length=128)
    auth_access_ttl_seconds: int = Field(default=900, ge=60, le=3_600)
    auth_refresh_ttl_seconds: int = Field(
        default=2_592_000,
        ge=3_600,
        le=7_776_000,
    )
    auth_access_cookie_name: str = Field(
        default="tmi_access",
        min_length=1,
        max_length=64,
    )
    auth_refresh_cookie_name: str = Field(
        default="tmi_refresh",
        min_length=1,
        max_length=64,
    )
    auth_csrf_cookie_name: str = Field(
        default="tmi_csrf",
        min_length=1,
        max_length=64,
    )
    auth_login_ip_limit: int = Field(default=20, ge=1, le=1_000)
    auth_login_email_limit: int = Field(default=10, ge=1, le=1_000)
    auth_login_rate_window_seconds: int = Field(
        default=900,
        ge=1,
        le=86_400,
    )
    auth_password_reset_ttl_seconds: int = Field(
        default=3_600,
        ge=300,
        le=86_400,
    )
    auth_password_reset_ip_limit: int = Field(default=10, ge=1, le=1_000)
    auth_password_reset_email_limit: int = Field(default=3, ge=1, le=1_000)
    auth_password_reset_rate_window_seconds: int = Field(
        default=900,
        ge=1,
        le=86_400,
    )
    firebase_project_id: str = Field(default="", max_length=255)
    firebase_auth_emulator_host: str = Field(default="", max_length=255)
    firebase_jwks_uri: str = Field(
        default="https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com",
        min_length=1,
        max_length=2_048,
    )
    firebase_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    staff_invitation_ttl_seconds: int = Field(
        default=86_400,
        ge=900,
        le=604_800,
    )
    firebase_totp_enabled: bool = False
    staff_mfa_max_age_seconds: int = Field(default=43_200, ge=300, le=86_400)
    oauth_rate_limit: int = Field(default=10, ge=1, le=100)
    oauth_rate_window_seconds: int = Field(default=60, ge=1, le=3_600)
    cloudinary_cloud_name: str = Field(default="", max_length=255)
    cloudinary_api_key: str = Field(default="", max_length=255)
    cloudinary_api_secret: SecretStr | None = None
    media_signature_ttl_seconds: int = Field(default=3_600, ge=3_600, le=3_600)
    media_delivery_ttl_seconds: int = Field(default=300, ge=60, le=3_600)
    media_avatar_max_bytes: int = Field(
        default=5_242_880,
        ge=1,
        le=20_971_520,
    )
    media_evidence_max_bytes: int = Field(
        default=31_457_280,
        ge=1,
        le=314_572_800,
    )
    document_verification_max_bytes: int = Field(
        default=26_214_400,
        ge=1,
        le=104_857_600,
    )
    media_provider_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    media_scanner_host: str = Field(default="clamav", min_length=1, max_length=255)
    media_scanner_port: int = Field(default=3310, ge=1, le=65_535)
    media_scanner_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    media_inspection_max_attempts: int = Field(default=5, ge=1, le=10)
    media_private_encryption_enabled: bool = False
    media_private_encryption_active_key_id: str = Field(default="", max_length=64)
    media_private_encryption_keys: Annotated[dict[str, SecretStr], NoDecode] = Field(
        default_factory=dict
    )
    media_upload_signature_rate_limit: int = Field(default=20, ge=1, le=1_000)
    media_upload_signature_rate_window_seconds: int = Field(default=60, ge=1, le=3_600)
    payment_provider: str = Field(default="mock", min_length=1, max_length=32)
    payment_amount_minor: int = Field(default=1_000_000, gt=0)
    payment_currency: str = Field(
        default="VND",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )
    payment_order_ttl_seconds: int = Field(default=900, ge=60, le=86_400)
    payment_webhook_secret: SecretStr | None = None
    payment_webhook_tolerance_seconds: int = Field(
        default=300,
        ge=30,
        le=900,
    )
    payment_checkout_base_url: str = Field(
        default="http://localhost:3000/payments/mock",
        min_length=1,
        max_length=2_048,
    )
    payos_base_url: str = Field(
        default="https://api-merchant.payos.vn",
        min_length=1,
        max_length=2_048,
    )
    payos_client_id: SecretStr | None = None
    payos_api_key: SecretStr | None = None
    payos_checksum_key: SecretStr | None = None
    payos_return_url: str = Field(default="", max_length=2_048)
    payos_cancel_url: str = Field(default="", max_length=2_048)
    payos_timeout_seconds: float = Field(default=8.0, gt=0, le=30)
    payment_real_money_test_enabled: bool = False
    payment_real_money_test_max_amount_vnd: int = Field(
        default=10_000,
        ge=1,
        le=100_000,
    )
    blockchain_network: Literal["local", "amoy", "polygon"] = "local"
    blockchain_chain_id: int = Field(default=31_337, gt=0)
    blockchain_rpc_url: str = Field(
        default="http://anvil:8545",
        min_length=1,
        max_length=2_048,
    )
    certificate_contract_address: str = Field(default="", max_length=42)
    blockchain_allowed_contract_addresses: str = Field(default="", max_length=8_192)
    blockchain_contract_abi_path: Path = Path(
        "../contracts/artifacts/CertificateRegistry.abi.json"
    )
    # This registry is additive: legacy CertificateRegistry configuration stays
    # independent so rollout can be disabled simply by leaving the address blank.
    thv_proof_registry_contract_address: str = Field(default="", max_length=42)
    thv_proof_registry_contract_abi_path: Path = Path(
        "../contracts/artifacts/THVProofRegistry.abi.json"
    )
    blockchain_signer_mode: Literal["local", "managed", "human"] = "local"
    blockchain_signer_private_key: SecretStr | None = None
    blockchain_managed_signer_url: str = Field(default="", max_length=2_048)
    blockchain_managed_signer_key_id: str = Field(default="", max_length=512)
    blockchain_managed_signer_expected_address: str = Field(default="", max_length=42)
    blockchain_managed_signer_timeout_seconds: float = Field(default=8.0, gt=0, le=30)
    blockchain_required_confirmations: int = Field(default=1, ge=1, le=1_000)
    blockchain_signing_enabled: bool = True
    blockchain_wallet_challenge_ttl_seconds: int = Field(
        default=600,
        ge=60,
        le=1_800,
    )
    blockchain_transaction_intent_ttl_seconds: int = Field(
        default=600,
        ge=60,
        le=1_800,
    )
    blockchain_nonce_lock_ttl_seconds: int = Field(default=30, ge=5, le=300)
    blockchain_explorer_base_url: str | None = Field(
        default=None,
        max_length=2_048,
    )

    @field_validator("blockchain_signer_private_key", mode="before")
    @classmethod
    def normalize_empty_blockchain_signer_private_key(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("media_private_encryption_keys", mode="before")
    @classmethod
    def parse_media_private_encryption_keys(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        """Accept map formats and the legacy single active-key value safely."""
        if not isinstance(value, str):
            return value
        serialized = value.strip()
        if not serialized:
            return {}
        active_key_id = info.data.get("media_private_encryption_active_key_id", "")
        if (
            serialized.startswith("{")
            and serialized.endswith("}")
            and ":" not in serialized
        ):
            if isinstance(active_key_id, str) and active_key_id:
                return {active_key_id: serialized[1:-1].strip()}
            if not info.data.get("media_private_encryption_enabled", False):
                return {}
        try:
            parsed = json.loads(serialized)
        except json.JSONDecodeError:
            try:
                parsed = literal_eval(serialized)
            except (SyntaxError, ValueError) as exc:
                raise ValueError(
                    "MEDIA_PRIVATE_ENCRYPTION_KEYS must be a key/value map."
                ) from exc
        if not isinstance(parsed, dict) or not all(
            isinstance(key, str) and isinstance(secret, str)
            for key, secret in parsed.items()
        ):
            raise ValueError("MEDIA_PRIVATE_ENCRYPTION_KEYS must be a key/value map.")
        return parsed

    @property
    def blockchain_contract_allowlist(self) -> frozenset[str]:
        return frozenset(
            item.strip().lower()
            for item in self.blockchain_allowed_contract_addresses.split(",")
            if item.strip()
        )

    @property
    def thv_proof_registry_configured(self) -> bool:
        """Whether the optional append-only proof registry is enabled."""
        return bool(self.thv_proof_registry_contract_address.strip())

    @property
    def business_workflows_enabled(self) -> bool:
        return self.release_mode == "full"

    @model_validator(mode="after")
    def validate_blockchain_configuration(self) -> Self:
        expected_chain_ids = {"local": 31_337, "amoy": 80_002, "polygon": 137}
        if self.blockchain_chain_id != expected_chain_ids[self.blockchain_network]:
            raise ValueError("Blockchain chain ID does not match the selected network.")

        address = self.certificate_contract_address
        if address and re.fullmatch(r"0x[0-9a-fA-F]{40}", address) is None:
            raise ValueError("Certificate contract address is invalid.")
        proof_registry_address = self.thv_proof_registry_contract_address.strip()
        if (
            proof_registry_address
            and re.fullmatch(r"0x[0-9a-fA-F]{40}", proof_registry_address) is None
        ):
            raise ValueError("THV proof registry contract address is invalid.")

        explorer_url = self.blockchain_explorer_base_url
        if explorer_url:
            parsed_explorer = urlsplit(explorer_url)
            local_http = (
                self.app_env == "local"
                and parsed_explorer.scheme == "http"
                and parsed_explorer.hostname in {"localhost", "127.0.0.1", "::1"}
            )
            if (
                (parsed_explorer.scheme != "https" and not local_http)
                or parsed_explorer.hostname is None
                or parsed_explorer.username is not None
                or parsed_explorer.password is not None
                or parsed_explorer.query
                or parsed_explorer.fragment
            ):
                raise ValueError("Blockchain explorer base URL is not allowed.")

        configured_addresses = self.blockchain_contract_allowlist
        if self.blockchain_network != "local":
            if not configured_addresses:
                raise ValueError(
                    "A contract address allowlist is required outside local mode."
                )
            if address.lower() not in configured_addresses:
                raise ValueError(
                    "The certificate contract address is not in the allowlist."
                )
            if (
                proof_registry_address
                and proof_registry_address.lower() not in configured_addresses
            ):
                raise ValueError(
                    "The THV proof registry contract address is not in the allowlist."
                )

        if self.app_env == "production" and self.release_mode == "preview":
            if self.blockchain_signer_private_key is not None:
                raise ValueError(
                    "Raw blockchain signer keys are forbidden in production."
                )
        if self.app_env == "production" and self.release_mode == "full":
            if self.blockchain_network != "polygon":
                raise ValueError("Production blockchain network must be Polygon PoS.")
            if not self.blockchain_rpc_url.startswith("https://"):
                raise ValueError("Production blockchain RPC must use HTTPS.")
            if self.blockchain_signer_mode != "human":
                raise ValueError(
                    "Production blockchain signing must be human-controlled."
                )
            if self.blockchain_signer_private_key is not None:
                raise ValueError(
                    "Raw blockchain signer keys are forbidden in production."
                )
            if not self.blockchain_signing_enabled:
                raise ValueError("Production blockchain signing must be enabled.")
        return self

    @model_validator(mode="after")
    def validate_runtime_integrations(self) -> Self:
        if (
            self.app_env == "production"
            and self.release_mode == "full"
            and not self.media_private_encryption_enabled
        ):
            raise ValueError(
                "Private document encryption must be enabled in production."
            )
        if self.app_env == "production" and self.release_mode == "full":
            cloudinary_secret = self.cloudinary_api_secret
            if (
                not self.cloudinary_cloud_name.strip()
                or not self.cloudinary_api_key.strip()
                or cloudinary_secret is None
                or not cloudinary_secret.get_secret_value().strip()
            ):
                raise ValueError(
                    "Cloudinary credentials are required for upload signatures "
                    "in a full production release."
                )
            if not self.media_scanner_host.strip():
                raise ValueError(
                    "A ClamAV scanner host is required for upload inspection "
                    "in a full production release."
                )
        if self.media_private_encryption_enabled:
            active_key_id = self.media_private_encryption_active_key_id
            if (
                re.fullmatch(r"[A-Za-z0-9._-]{1,64}", active_key_id) is None
                or active_key_id not in self.media_private_encryption_keys
            ):
                raise ValueError(
                    "An active private document encryption key is required."
                )
            for key_id, secret in self.media_private_encryption_keys.items():
                if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", key_id) is None:
                    raise ValueError("A document encryption key ID is invalid.")
                try:
                    decoded_key = base64.b64decode(
                        secret.get_secret_value(), validate=True
                    )
                except (binascii.Error, ValueError) as exc:
                    raise ValueError(
                        "Document encryption keys must be valid base64."
                    ) from exc
                if len(decoded_key) != 32:
                    raise ValueError(
                        "Document encryption keys must decode to exactly 32 bytes."
                    )
        if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", self.audit_integrity_key_id) is None:
            raise ValueError("Active audit integrity key ID is invalid.")
        for key_id, key in self.audit_integrity_verification_keys.items():
            if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", key_id) is None:
                raise ValueError("Audit integrity verification key ID is invalid.")
            if len(key.get_secret_value()) < 32:
                raise ValueError(
                    "Each audit integrity verification key must contain at least "
                    "32 characters."
                )
        historical_active = self.audit_integrity_verification_keys.get(
            self.audit_integrity_key_id
        )
        if (
            historical_active is not None
            and self.audit_integrity_key is not None
            and historical_active.get_secret_value()
            != self.audit_integrity_key.get_secret_value()
        ):
            raise ValueError(
                "The active audit key ID cannot map to different key material."
            )
        if self.app_env == "production" and (
            self.audit_integrity_key is None
            or len(self.audit_integrity_key.get_secret_value()) < 32
        ):
            raise ValueError(
                "A dedicated audit integrity key of at least 32 characters is "
                "required in production."
            )
        if self.app_env != "local" and self.firebase_auth_emulator_host.strip():
            raise ValueError("Firebase Auth emulator is local-only.")
        if (
            self.app_env == "production"
            and self.release_mode == "full"
            and not self.firebase_totp_enabled
        ):
            raise ValueError("Firebase TOTP MFA must be enabled in production.")
        provider = self.payment_provider.strip().lower()
        if provider not in {"disabled", "mock", "payos"}:
            raise ValueError("Payment provider must be disabled, mock or payos.")
        if provider == "disabled" and self.release_mode != "preview":
            raise ValueError("Disabled payments are allowed only in preview mode.")
        if self.release_mode == "preview" and provider != "disabled":
            raise ValueError("Preview mode requires the disabled payment provider.")
        is_mock_provider = provider == "mock"
        if (
            self.app_env == "local"
            and self.release_mode == "full"
            and not is_mock_provider
        ):
            raise ValueError("Local payment provider must be mock.")
        if self.app_env != "local" and self.release_mode == "full" and is_mock_provider:
            raise ValueError(
                "Mock payment provider is local-only; configure a production "
                "payment adapter."
            )
        if self.app_env != "local" and self.release_mode == "full":
            missing_payos_secret = any(
                secret is None or not secret.get_secret_value()
                for secret in (
                    self.payos_client_id,
                    self.payos_api_key,
                    self.payos_checksum_key,
                )
            )
            if missing_payos_secret:
                raise ValueError(
                    "payOS Client ID, API Key and Checksum Key are required "
                    "outside local mode."
                )
            if not self.payos_base_url.startswith("https://"):
                raise ValueError("payOS API URL must use HTTPS outside local mode.")
            if not self.payos_return_url.startswith("https://"):
                raise ValueError("payOS return URL must use HTTPS outside local mode.")
            if not self.payos_cancel_url.startswith("https://"):
                raise ValueError("payOS cancel URL must use HTTPS outside local mode.")
        if self.payment_real_money_test_enabled and self.app_env == "production":
            raise ValueError("Real-money test mode cannot be enabled in production.")
        return self

    public_rate_limit: int = Field(default=120, ge=1, le=10_000)
    public_rate_window_seconds: int = Field(default=60, ge=1, le=3_600)
    public_catalog_cache_ttl_seconds: int = Field(default=60, ge=1, le=3_600)
    ranking_cache_ttl_seconds: int = Field(default=30, ge=1, le=300)
    voting_summary_cache_ttl_seconds: int = Field(default=30, ge=1, le=300)
    search_statement_timeout_ms: int = Field(default=400, ge=50, le=5_000)
    search_trigram_min_length: int = Field(default=4, ge=3, le=20)
    search_trigram_threshold: float = Field(default=0.3, ge=0.1, le=0.9)
    search_trigram_max_boost: float = Field(default=0.25, ge=0.0, le=0.5)
    search_rate_limit: int = Field(default=60, ge=1, le=10_000)
    search_rate_window_seconds: int = Field(default=60, ge=1, le=3_600)
    search_autocomplete_cache_ttl_seconds: int = Field(
        default=60,
        ge=1,
        le=600,
    )
    search_trending_minimum_count: int = Field(default=5, ge=3, le=1_000)
    search_history_retention_days: int = Field(default=90, ge=1, le=365)
    search_history_list_limit: int = Field(default=10, ge=1, le=50)
    public_sitemap_page_size: int = Field(default=10_000, ge=1, le=50_000)
    public_sitemap_cache_ttl_seconds: int = Field(
        default=86_400,
        ge=300,
        le=604_800,
    )
    public_report_rate_limit: int = Field(default=5, ge=1, le=100)
    public_report_rate_window_seconds: int = Field(default=3_600, ge=60, le=86_400)
    public_engagement_rate_limit: int = Field(default=30, ge=1, le=1_000)
    public_engagement_rate_window_seconds: int = Field(
        default=60,
        ge=1,
        le=3_600,
    )
    engagement_view_dedupe_ttl_seconds: int = Field(
        default=86_400,
        ge=60,
        le=172_800,
    )
    engagement_visitor_cookie_name: str = Field(
        default="tmi_engagement_visitor",
        min_length=1,
        max_length=64,
    )
    engagement_visitor_hmac_secret: SecretStr | None = None
    engagement_activity_retention_days: int = Field(default=365, ge=30, le=3_650)
    voting_user_rate_limit: int = Field(default=20, ge=1, le=10_000)
    voting_ip_rate_limit: int = Field(default=100, ge=1, le=50_000)
    voting_rate_window_seconds: int = Field(default=60, ge=1, le=3_600)
    public_verification_cache_ttl_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
    )
    certificate_validity_days: int = Field(default=365, ge=1, le=3_650)
    certificate_template_version: str = Field(
        default="certificate-red-gold-v1",
        min_length=1,
        max_length=64,
    )
    smtp_host: str = Field(default="localhost", min_length=1, max_length=255)
    smtp_port: int = Field(default=1025, ge=1, le=65_535)
    smtp_sender: str = Field(
        default="no-reply@tmigroup.vn", min_length=3, max_length=320
    )
    smtp_username: str | None = Field(default=None, min_length=1, max_length=320)
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = False
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = Field(default=20, ge=1, le=120)

    @property
    def cors_origins(self) -> tuple[str, ...]:
        origins = tuple(
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        )
        if "*" in origins:
            raise ValueError("CORS wildcard origins are not allowed.")
        if self.app_env == "production" and any(
            not origin.startswith("https://") for origin in origins
        ):
            raise ValueError("Production CORS origins must use HTTPS.")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
