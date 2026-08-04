import asyncio
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.errors import DossierForbiddenError
from app.modules.dossiers.models import DossierStatus
from app.modules.reviews.dependencies import get_precheck_service
from app.modules.reviews.types import DossierTransitionView


class StubPrecheckService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, UUID, str]] = []
        self.forbidden = False

    async def _transition(
        self,
        action: str,
        dossier_id: UUID,
        reason: str,
        status: DossierStatus,
    ) -> DossierTransitionView:
        if self.forbidden:
            raise DossierForbiddenError()
        self.calls.append((action, dossier_id, reason))
        return DossierTransitionView(dossier_id=dossier_id, status=status)

    async def start_precheck(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reason: str,
    ) -> DossierTransitionView:
        return await self._transition(
            "precheck",
            dossier_id,
            reason,
            DossierStatus.PRECHECK,
        )

    async def pass_precheck(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reason: str,
    ) -> DossierTransitionView:
        return await self._transition(
            "pass-precheck",
            dossier_id,
            reason,
            DossierStatus.UNDER_REVIEW,
        )

    async def request_supplement(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reason: str,
    ) -> DossierTransitionView:
        return await self._transition(
            "request-supplement",
            dossier_id,
            reason,
            DossierStatus.NEEDS_SUPPLEMENT,
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="admin@tmigroup.vn",
        roles=("SUPER_ADMIN",),
    )


async def _request(
    method: str,
    path: str,
    service: StubPrecheckService,
    *,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    principal = _principal()
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_precheck_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_admin_precheck_transition_contract() -> None:
    dossier_id = uuid4()
    service = StubPrecheckService()
    base = f"/api/v1/admin/dossiers/{dossier_id}"

    precheck = asyncio.run(
        _request(
            "POST",
            f"{base}/precheck",
            service,
            json={"reason": "Bắt đầu tiền kiểm."},
        )
    )
    passed = asyncio.run(
        _request(
            "POST",
            f"{base}/pass-precheck",
            service,
            json={"reason": "Đã qua checklist."},
        )
    )
    supplement = asyncio.run(
        _request(
            "POST",
            f"{base}/request-supplement",
            service,
            json={"reason": "Cần bổ sung nguồn."},
        )
    )

    assert precheck.status_code == passed.status_code == supplement.status_code == 200
    assert precheck.json()["data"] == {
        "dossierId": str(dossier_id),
        "status": "PRECHECK",
    }
    assert passed.json()["data"]["status"] == "UNDER_REVIEW"
    assert supplement.json()["data"]["status"] == "NEEDS_SUPPLEMENT"
    assert [call[0] for call in service.calls] == [
        "precheck",
        "pass-precheck",
        "request-supplement",
    ]


def test_admin_precheck_validates_reason_and_preserves_forbidden_contract() -> None:
    dossier_id = uuid4()
    service = StubPrecheckService()
    base = f"/api/v1/admin/dossiers/{dossier_id}"

    invalid = asyncio.run(
        _request("POST", f"{base}/precheck", service, json={"reason": ""})
    )
    service.forbidden = True
    forbidden = asyncio.run(
        _request(
            "POST",
            f"{base}/precheck",
            service,
            json={"reason": "Không đủ quyền."},
        )
    )

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "DOSSIER_FORBIDDEN"
