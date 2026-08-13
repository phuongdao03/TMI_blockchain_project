import asyncio
from uuid import uuid4

import httpx

from app.core.config import Settings, get_settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_firebase_auth_runtime,
    get_session_service,
)
from app.modules.auth.firebase_provider import FirebaseClaims
from app.modules.auth.models import AccountType
from app.modules.auth.oauth_service import OAuthCompletion
from app.modules.auth.session_service import AuthPrincipal, IssuedSession


class FakeRateLimiter:
    async def check(self, client_ip: str) -> None:
        del client_ip


class FakeVerifier:
    async def validate_id_token(self, id_token: str) -> FirebaseClaims:
        assert len(id_token) >= 100
        return FirebaseClaims(
            subject="firebase-user-1",
            email="viewer@example.com",
            email_verified=True,
            name="Viewer",
            picture=None,
        )


class FakeAccountService:
    async def complete(self, **kwargs: object) -> OAuthCompletion:
        del kwargs
        return OAuthCompletion(
            user_id=uuid4(),
            issued=IssuedSession("access", "refresh", "csrf"),
        )


class FakeSessionService:
    async def authenticate_access(self, access_token: str) -> AuthPrincipal:
        assert access_token == "access"
        return AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="viewer@example.com",
            roles=(),
            account_type=AccountType.PUBLIC_USER,
        )


def test_firebase_exchange_is_the_only_google_auth_surface() -> None:
    async def scenario() -> None:
        settings = Settings(app_env="local", firebase_project_id="tmi-local")
        runtime = type(
            "Runtime",
            (),
            {
                "rate_limiter": FakeRateLimiter(),
                "verifier": FakeVerifier(),
                "account_service": FakeAccountService(),
            },
        )()
        app = create_application(settings=settings, health_service=HealthService({}))
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_firebase_auth_runtime] = lambda: runtime
        app.dependency_overrides[get_session_service] = lambda: FakeSessionService()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                exchange = await client.post(
                    "/api/v1/auth/firebase/exchange",
                    json={
                        "idToken": "x" * 100,
                        "accountType": "PUBLIC_USER",
                    },
                )
                assert exchange.status_code == 200
                assert len(exchange.headers.get_list("set-cookie")) == 3
                assert (
                    await client.post("/api/v1/auth/oauth/google/start", json={})
                ).status_code == 404
                assert (
                    await client.get("/api/v1/auth/oauth/google/callback")
                ).status_code == 404
        app.dependency_overrides.clear()

    asyncio.run(scenario())


def test_legacy_google_secret_configuration_is_removed() -> None:
    fields = Settings.model_fields
    assert not any(name.startswith("google_oidc_") for name in fields)
    assert "oauth_state_ttl_seconds" not in fields
