import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_applicant_upgrade_service,
    get_csrf_protected_principal,
    get_current_principal,
    get_session_service,
)
from app.modules.auth.models import AccountType
from app.modules.auth.onboarding import ApplicantUpgradeResult
from app.modules.auth.session_service import (
    AuthPrincipal,
    ClientMetadata,
    IssuedSession,
    SessionView,
)


class StubSessionService:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.session_id = uuid4()
        self.principal = AuthPrincipal(
            user_id=self.user_id,
            session_id=self.session_id,
            email="owner@tmigroup.vn",
            roles=("APPLICANT",),
        )
        self.login_metadata: ClientMetadata | None = None
        self.refreshed = False
        self.logged_out = False
        self.revoked_session_id: UUID | None = None

    async def login(
        self,
        *,
        email: str,
        password: str,
        metadata: ClientMetadata,
    ) -> IssuedSession:
        self.login_metadata = metadata
        return self._issued()

    async def authenticate_access(self, access_token: str) -> AuthPrincipal:
        return self.principal

    async def refresh(
        self,
        *,
        refresh_token: str,
        csrf_cookie: str | None,
        csrf_header: str | None,
        metadata: ClientMetadata,
    ) -> IssuedSession:
        self.refreshed = True
        return self._issued()

    async def logout(
        self,
        *,
        refresh_token: str,
        csrf_cookie: str | None,
        csrf_header: str | None,
    ) -> None:
        self.logged_out = True

    async def list_sessions(
        self,
        principal: AuthPrincipal,
    ) -> tuple[SessionView, ...]:
        now = datetime.now(UTC)
        return (
            SessionView(
                id=self.session_id,
                device_name="Laptop",
                user_agent="Test browser",
                created_at=now,
                expires_at=now,
                is_current=True,
            ),
        )

    async def revoke_session(
        self,
        *,
        principal: AuthPrincipal,
        target_session_id: UUID,
        csrf_cookie: str | None,
        csrf_header: str | None,
    ) -> None:
        self.revoked_session_id = target_session_id

    @staticmethod
    def _issued() -> IssuedSession:
        return IssuedSession(
            access_token="access-token-value",
            refresh_token="refresh-token-value",
            csrf_token="csrf-token-value",
        )


class StubApplicantUpgradeService:
    async def upgrade(
        self,
        principal: AuthPrincipal,
        *,
        account_type: AccountType,
    ) -> ApplicantUpgradeResult:
        return ApplicantUpgradeResult(
            user_id=principal.user_id,
            email=principal.email,
            account_type=account_type,
            roles=("APPLICANT",),
        )


async def _request(
    method: str,
    path: str,
    service: StubSessionService,
    *,
    json: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    upgrade_service: StubApplicantUpgradeService | None = None,
) -> httpx.Response:
    settings = Settings.model_validate(
        {
            "app_env": "local",
            "auth_access_cookie_name": "tmi_access",
            "auth_refresh_cookie_name": "tmi_refresh",
            "auth_csrf_cookie_name": "tmi_csrf",
        }
    )
    app = create_application(
        settings=settings,
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_session_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: service.principal
    app.dependency_overrides[get_csrf_protected_principal] = (
        lambda: service.principal
    )
    if upgrade_service is not None:
        app.dependency_overrides[get_applicant_upgrade_service] = (
            lambda: upgrade_service
        )
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            cookies=cookies,
        ) as client:
            return await client.request(
                method,
                path,
                json=json,
                headers=headers,
            )


def test_login_api_sets_secure_cookie_contract_without_returning_tokens() -> None:
    service = StubSessionService()
    response = asyncio.run(
        _request(
            "POST",
            "/api/v1/auth/login",
            service,
            json={
                "email": "owner@tmigroup.vn",
                "password": "correct horse battery staple",
                "deviceName": "Work laptop",
            },
        )
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "user": {
            "email": "owner@tmigroup.vn",
            "id": str(service.user_id),
            "roles": ["APPLICANT"],
            "accountType": None,
        }
    }
    assert "token" not in response.text.lower()
    cookies = response.headers.get_list("set-cookie")
    access_cookie = next(value for value in cookies if value.startswith("tmi_access="))
    refresh_cookie = next(
        value for value in cookies if value.startswith("tmi_refresh=")
    )
    csrf_cookie = next(value for value in cookies if value.startswith("tmi_csrf="))
    assert "HttpOnly" in access_cookie
    assert "HttpOnly" in refresh_cookie
    assert "HttpOnly" not in csrf_cookie
    assert all("SameSite=lax" in value for value in cookies)
    assert service.login_metadata is not None
    assert service.login_metadata.device_name == "Work laptop"


def test_me_and_sessions_api_return_current_user_scope() -> None:
    service = StubSessionService()
    me_response = asyncio.run(_request("GET", "/api/v1/auth/me", service))
    sessions_response = asyncio.run(_request("GET", "/api/v1/auth/sessions", service))

    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == "owner@tmigroup.vn"
    assert sessions_response.status_code == 200
    assert sessions_response.json()["data"][0]["isCurrent"] is True


def test_refresh_logout_and_revoke_session_use_cookie_csrf_contract() -> None:
    service = StubSessionService()
    cookies = {
        "tmi_access": "access-token",
        "tmi_refresh": "refresh-token",
        "tmi_csrf": "csrf-token",
    }
    headers = {"X-CSRF-Token": "csrf-token"}

    refresh_response = asyncio.run(
        _request(
            "POST",
            "/api/v1/auth/refresh",
            service,
            cookies=cookies,
            headers=headers,
        )
    )
    revoke_response = asyncio.run(
        _request(
            "DELETE",
            f"/api/v1/auth/sessions/{service.session_id}",
            service,
            cookies=cookies,
            headers=headers,
        )
    )
    logout_response = asyncio.run(
        _request(
            "POST",
            "/api/v1/auth/logout",
            service,
            cookies=cookies,
            headers=headers,
        )
    )

    assert refresh_response.status_code == 200
    assert revoke_response.status_code == 200
    assert logout_response.status_code == 200
    assert service.refreshed is True
    assert service.revoked_session_id == service.session_id
    assert service.logged_out is True
    assert "Max-Age=0" in logout_response.headers["set-cookie"]


def test_applicant_upgrade_api_returns_updated_account_scope() -> None:
    service = StubSessionService()
    response = asyncio.run(
        _request(
            "POST",
            "/api/v1/auth/applicant-upgrade",
            service,
            json={"accountType": "INDIVIDUAL_APPLICANT"},
            upgrade_service=StubApplicantUpgradeService(),
        )
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": str(service.user_id),
        "email": "owner@tmigroup.vn",
        "roles": ["APPLICANT"],
        "accountType": "INDIVIDUAL_APPLICANT",
    }
