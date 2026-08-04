import asyncio
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.errors import CsrfValidationError, UnauthenticatedError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.users.dependencies import get_user_profile_service
from app.modules.users.service import ProfileChanges, ProfileView


class StubUserProfileService:
    def __init__(self, principal: AuthPrincipal) -> None:
        self.principal = principal
        self.changes: ProfileChanges | None = None

    async def get_profile(self, *, user_id: object, email: str) -> ProfileView:
        return self._view()

    async def update_profile(
        self,
        *,
        user_id: object,
        email: str,
        changes: ProfileChanges,
    ) -> ProfileView:
        self.changes = changes
        return self._view(full_name=changes.full_name, phone=changes.phone)

    def _view(
        self,
        *,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> ProfileView:
        return ProfileView(
            user_id=self.principal.user_id,
            email=self.principal.email,
            full_name=full_name,
            phone=phone,
            avatar_media_id=None,
            locale="vi",
            timezone="Asia/Ho_Chi_Minh",
        )


async def _request(
    method: str,
    path: str,
    service: StubUserProfileService,
    principal: AuthPrincipal,
    *,
    json: dict[str, object] | None = None,
    auth_error: Exception | None = None,
    csrf_error: Exception | None = None,
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_user_profile_service] = lambda: service

    async def current_principal() -> AuthPrincipal:
        if auth_error is not None:
            raise auth_error
        return principal

    async def csrf_principal() -> AuthPrincipal:
        if csrf_error is not None:
            raise csrf_error
        return principal

    app.dependency_overrides[get_current_principal] = current_principal
    app.dependency_overrides[get_csrf_protected_principal] = csrf_principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_profile_api_reads_and_patches_current_user() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )
    service = StubUserProfileService(principal)

    get_response = asyncio.run(_request("GET", "/api/v1/users/me", service, principal))
    patch_response = asyncio.run(
        _request(
            "PATCH",
            "/api/v1/users/me",
            service,
            principal,
            json={
                "fullName": "Nguyễn Minh Anh",
                "phone": "+84901234567",
                "locale": "vi",
                "timezone": "Asia/Ho_Chi_Minh",
            },
        )
    )

    assert get_response.status_code == 200
    assert get_response.json()["data"]["email"] == "owner@tmigroup.vn"
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["fullName"] == "Nguyễn Minh Anh"
    assert service.changes is not None
    assert service.changes.provided_fields == {
        "full_name",
        "phone",
        "locale",
        "timezone",
    }


def test_profile_api_enforces_auth_csrf_and_field_validation() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )
    service = StubUserProfileService(principal)

    unauthorized = asyncio.run(
        _request(
            "GET",
            "/api/v1/users/me",
            service,
            principal,
            auth_error=UnauthenticatedError(),
        )
    )
    forbidden = asyncio.run(
        _request(
            "PATCH",
            "/api/v1/users/me",
            service,
            principal,
            json={"fullName": "Tên hợp lệ"},
            csrf_error=CsrfValidationError(),
        )
    )
    invalid = asyncio.run(
        _request(
            "PATCH",
            "/api/v1/users/me",
            service,
            principal,
            json={"phone": "not-a-phone"},
        )
    )

    assert unauthorized.status_code == 401
    assert forbidden.status_code == 403
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
