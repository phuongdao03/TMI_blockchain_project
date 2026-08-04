import asyncio

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import get_password_reset_service


class StubPasswordResetService:
    def __init__(self) -> None:
        self.request: tuple[str, str] | None = None
        self.reset: tuple[str, str] | None = None

    async def request_reset(self, *, email: str, client_ip: str) -> None:
        self.request = (email, client_ip)

    async def reset_password(self, *, token: str, new_password: str) -> None:
        self.reset = (token, new_password)


async def _post(
    path: str,
    payload: dict[str, str],
    service: StubPasswordResetService,
) -> httpx.Response:
    settings = Settings.model_validate({"app_env": "local"})
    app = create_application(
        settings=settings,
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_password_reset_service] = lambda: service
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            cookies={
                settings.auth_access_cookie_name: "access",
                settings.auth_refresh_cookie_name: "refresh",
                settings.auth_csrf_cookie_name: "csrf",
            },
        ) as client:
            return await client.post(
                path,
                json=payload,
            )


def test_forgot_password_api_always_returns_generic_accepted_response() -> None:
    service = StubPasswordResetService()
    response = asyncio.run(
        _post(
            "/api/v1/auth/forgot-password",
            {"email": "Unknown@TMIGroup.vn"},
            service,
        )
    )

    assert response.status_code == 202
    assert response.json()["data"] == {
        "message": ("If the address exists, password reset instructions will be sent.")
    }
    assert service.request == ("Unknown@tmigroup.vn", "127.0.0.1")


def test_reset_password_api_consumes_token_and_clears_auth_cookies() -> None:
    service = StubPasswordResetService()
    token = "r" * 43
    response = asyncio.run(
        _post(
            "/api/v1/auth/reset-password",
            {
                "token": token,
                "newPassword": "new correct horse battery staple",
            },
            service,
        )
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "password_reset"}
    assert service.reset == (token, "new correct horse battery staple")
    deleted_cookies = response.headers.get_list("set-cookie")
    assert len(deleted_cookies) == 3
    assert all("Max-Age=0" in cookie for cookie in deleted_cookies)
