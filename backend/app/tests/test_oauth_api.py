import asyncio
from uuid import uuid4

import httpx

from app.core.config import Settings, get_settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_oauth_runtime,
    get_session_service,
)
from app.modules.auth.models import AccountType
from app.modules.auth.oauth import OAuthAttempt
from app.modules.auth.oauth_provider import GoogleOIDCClaims
from app.modules.auth.oauth_service import OAuthCompletion
from app.modules.auth.session_service import AuthPrincipal, IssuedSession


class FakeStateStore:
    def __init__(self) -> None:
        self.attempts: dict[str, OAuthAttempt] = {}

    async def save(self, attempt: OAuthAttempt) -> None:
        self.attempts[attempt.state] = attempt

    async def consume(self, state: str) -> OAuthAttempt | None:
        return self.attempts.pop(state, None)


class FakeRateLimiter:
    async def check(self, client_ip: str) -> None:
        del client_ip


class FakeProvider:
    def authorization_url(self, attempt: OAuthAttempt) -> str:
        return f"https://accounts.google.test/auth?state={attempt.state}"

    async def exchange_code(self, code: str) -> str:
        assert code == "authorization-code"
        return "id-token"

    async def validate_id_token(
        self,
        id_token: str,
        *,
        expected_nonce: str,
    ) -> GoogleOIDCClaims:
        assert id_token == "id-token"
        assert expected_nonce == "nonce"
        return GoogleOIDCClaims(
            subject="google-subject",
            email="viewer@gmail.com",
            email_verified=True,
            name="Viewer",
            picture=None,
        )


class FakeAccountService:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.completions = 0

    async def complete(self, **kwargs: object) -> OAuthCompletion:
        del kwargs
        self.completions += 1
        return OAuthCompletion(
            user_id=self.user_id,
            issued=IssuedSession("access", "refresh", "csrf"),
        )


class FakeSessionService:
    async def authenticate_access(self, access_token: str) -> AuthPrincipal:
        assert access_token in {"access", "existing-access"}
        return AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="viewer@gmail.com",
            roles=("SUPER_ADMIN",),
            account_type=AccountType.PUBLIC_USER,
        )


def test_google_start_and_callback_use_cookie_session_and_role_redirect() -> None:
    async def scenario() -> None:
        settings = Settings.model_validate(
            {
                "app_env": "local",
                "app_base_url": "http://localhost:3000",
                "auth_access_cookie_name": "tmi_access",
                "auth_refresh_cookie_name": "tmi_refresh",
                "auth_csrf_cookie_name": "tmi_csrf",
            }
        )
        state_store = FakeStateStore()
        account_service = FakeAccountService()
        runtime = type(
            "Runtime",
            (),
            {
                "state_store": state_store,
                "rate_limiter": FakeRateLimiter(),
                "provider": FakeProvider(),
                "account_service": account_service,
            },
        )()
        session_service = FakeSessionService()
        app = create_application(
            settings=settings,
            health_service=HealthService({}),
        )
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_oauth_runtime] = lambda: runtime
        app.dependency_overrides[get_session_service] = lambda: session_service
        app.dependency_overrides[get_csrf_protected_principal] = lambda: AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="viewer@gmail.com",
            roles=(),
        )
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                start = await client.post(
                    "/api/v1/auth/oauth/google/start",
                    json={
                        "accountType": "PUBLIC_USER",
                        "next": "/dashboard",
                    },
                )
                assert start.status_code == 200
                state = next(iter(state_store.attempts))
                assert start.json()["data"]["authorizationUrl"].endswith(
                    f"state={state}"
                )

                state_store.attempts[state] = OAuthAttempt(
                    state=state,
                    nonce="nonce",
                    account_type="PUBLIC_USER",
                    next_path="/dashboard",
                )
                callback = await client.get(
                    "/api/v1/auth/oauth/google/callback"
                    f"?code=authorization-code&state={state}",
                    cookies={"tmi_access": "existing-access"},
                    follow_redirects=False,
                )
                assert callback.status_code == 303
                assert callback.headers["location"] == (
                    "http://localhost:3000/admin/dashboard"
                )
                assert len(callback.headers.get_list("set-cookie")) == 3
                assert account_service.completions == 1

        app.dependency_overrides.clear()

    asyncio.run(scenario())
