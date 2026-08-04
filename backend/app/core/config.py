from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Source: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "staging", "production"] = "local"
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
    readiness_timeout_seconds: float = Field(default=1.0, gt=0, le=10)
    auth_outbox_encryption_key: SecretStr | None = None
    pii_encryption_key: SecretStr | None = None
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
    google_oidc_client_id: str = Field(default="", max_length=255)
    google_oidc_client_secret: SecretStr | None = None
    google_oidc_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/oauth/google/callback",
        min_length=1,
        max_length=2_048,
    )
    google_oidc_authorization_endpoint: str = Field(
        default="https://accounts.google.com/o/oauth2/v2/auth",
        min_length=1,
        max_length=2_048,
    )
    google_oidc_token_endpoint: str = Field(
        default="https://oauth2.googleapis.com/token",
        min_length=1,
        max_length=2_048,
    )
    google_oidc_jwks_uri: str = Field(
        default="https://www.googleapis.com/oauth2/v3/certs",
        min_length=1,
        max_length=2_048,
    )
    google_oidc_issuer: str = Field(
        default="https://accounts.google.com",
        min_length=1,
        max_length=255,
    )
    google_oidc_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    oauth_state_ttl_seconds: int = Field(default=300, ge=60, le=900)
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
        default=20_971_520,
        ge=1,
        le=104_857_600,
    )
    media_provider_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
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
        default="http://localhost:3000/thanh-toan/mock",
        min_length=1,
        max_length=2_048,
    )
    blockchain_network: Literal["local", "amoy"] = "local"
    blockchain_chain_id: int = Field(default=31_337, gt=0)
    blockchain_rpc_url: str = Field(
        default="http://anvil:8545",
        min_length=1,
        max_length=2_048,
    )
    certificate_contract_address: str = Field(default="", max_length=42)
    blockchain_contract_abi_path: Path = Path(
        "../contracts/artifacts/CertificateRegistry.abi.json"
    )
    blockchain_signer_private_key: SecretStr | None = None
    blockchain_required_confirmations: int = Field(default=1, ge=1, le=1_000)
    blockchain_nonce_lock_ttl_seconds: int = Field(default=30, ge=5, le=300)
    blockchain_explorer_base_url: str | None = Field(
        default=None,
        max_length=2_048,
    )
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
