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
from app.modules.ranking.recount import RankingRecountRequest, RankingRecountService
from app.modules.ranking.recount_dependencies import get_ranking_recount_service

CAMPAIGN_ID = UUID("30000000-0000-0000-0000-000000000001")


class StubRankingRecountService:
    def __init__(self) -> None:
        self.received: tuple[UUID, UUID, str | None] | None = None

    async def request(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        request_id: str | None = None,
    ) -> RankingRecountRequest:
        self.received = (principal.user_id, campaign_id, request_id)
        return RankingRecountRequest(campaign_id=campaign_id)


def test_ranking_recount_admin_api_enqueues_with_request_context() -> None:
    service = StubRankingRecountService()
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="admin@tmigroup.vn",
        roles=("SUPER_ADMIN",),
    )
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_ranking_recount_service] = lambda: service
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal

    async def request() -> httpx.Response:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                return await client.post(
                    f"/api/v1/admin/ranking/campaigns/{CAMPAIGN_ID}/recount"
                )

    response = asyncio.run(request())

    assert response.status_code == 202
    assert response.json()["data"] == {
        "campaignId": str(CAMPAIGN_ID),
        "status": "queued",
    }
    assert service.received is not None
    assert service.received[:2] == (principal.user_id, CAMPAIGN_ID)
    assert isinstance(service.received[2], str)


def test_ranking_recount_admin_api_rejects_non_system_admin() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="content@tmigroup.vn",
        roles=("CONTENT_ADMIN",),
    )
    service = RankingRecountService(enqueue=lambda *_: None)
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_ranking_recount_service] = lambda: service
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal

    async def request() -> httpx.Response:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                return await client.post(
                    f"/api/v1/admin/ranking/campaigns/{CAMPAIGN_ID}/recount"
                )

    response = asyncio.run(request())

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "RANKING_RECOUNT_FORBIDDEN"
