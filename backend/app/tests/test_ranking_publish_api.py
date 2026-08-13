import asyncio
from datetime import UTC, datetime
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
from app.modules.ranking.publish import RankingPublicationResult
from app.modules.ranking.publish_dependencies import get_ranking_publication_service

CAMPAIGN_ID = UUID("30000000-0000-0000-0000-000000000001")
SNAPSHOT_ID = UUID("60000000-0000-0000-0000-000000000001")


class StubRankingPublicationService:
    async def publish(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        version: int,
        request_id: str | None = None,
    ) -> RankingPublicationResult:
        assert principal.roles == ("SUPER_ADMIN",)
        assert campaign_id == CAMPAIGN_ID
        assert version == 3
        assert request_id is not None
        return RankingPublicationResult(
            campaign_id=campaign_id,
            snapshot_id=SNAPSHOT_ID,
            version=version,
            published_at=datetime(2026, 8, 3, 8, tzinfo=UTC),
        )


def test_ranking_publish_api_returns_selected_snapshot() -> None:
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
    app.dependency_overrides[get_ranking_publication_service] = lambda: (
        StubRankingPublicationService()
    )
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal

    async def request() -> httpx.Response:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                return await client.post(
                    f"/api/v1/admin/ranking/campaigns/{CAMPAIGN_ID}/publish",
                    json={"version": 3},
                )

    response = asyncio.run(request())

    assert response.status_code == 200
    assert response.json()["data"] == {
        "campaignId": str(CAMPAIGN_ID),
        "snapshotId": str(SNAPSHOT_ID),
        "version": 3,
        "publishedAt": "2026-08-03T08:00:00Z",
    }
