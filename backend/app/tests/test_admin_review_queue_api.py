import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import DossierStatus
from app.modules.reviews.dependencies import get_review_service
from app.modules.reviews.types import (
    AdminReviewDossierDetailView,
    AdminReviewDossierPage,
    AdminReviewDossierSummaryView,
)

NOW = datetime(2026, 9, 7, 4, 0, tzinfo=UTC)


class StubReviewService:
    def __init__(self) -> None:
        self.dossier_id = uuid4()
        self.status: DossierStatus | None = None

    async def list_admin_dossiers(
        self,
        principal: AuthPrincipal,
        *,
        status: DossierStatus | None,
        page: int,
        page_size: int,
    ) -> AdminReviewDossierPage:
        self.status = status
        return AdminReviewDossierPage(
            items=(
                AdminReviewDossierSummaryView(
                    dossier_id=self.dossier_id,
                    dossier_code="TMI-2026-QUEUE",
                    dossier_title="Hồ sơ chờ phân công",
                    status=DossierStatus.SUBMITTED,
                    version_no=1,
                    submitted_at=NOW,
                    assignment_count=0,
                ),
            ),
            total=1,
        )

    async def get_admin_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> AdminReviewDossierDetailView:
        assert dossier_id == self.dossier_id
        return AdminReviewDossierDetailView(
            dossier_id=dossier_id,
            dossier_code="TMI-2026-QUEUE",
            dossier_title="Hồ sơ chờ phân công",
            status=DossierStatus.SUBMITTED,
            version_no=1,
            submitted_at=NOW,
            assignment_count=0,
            canonical_hash="a" * 64,
            snapshot_json={
                "dossier": {"title": "Hồ sơ chờ phân công"},
                "evidences": [],
            },
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="admin@tmigroup.vn",
        roles=("SUPER_ADMIN",),
        permissions=("review.assign",),
    )


async def _request(path: str, service: StubReviewService) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_review_service] = lambda: service
    app.dependency_overrides[get_current_principal] = _principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.get(path)


def test_admin_review_queue_list_and_detail_contract() -> None:
    service = StubReviewService()
    listed = asyncio.run(
        _request(
            "/api/v1/admin/review-dossiers?status=SUBMITTED&page=1&pageSize=20",
            service,
        )
    )
    detail = asyncio.run(
        _request(f"/api/v1/admin/review-dossiers/{service.dossier_id}", service)
    )

    assert listed.status_code == 200
    assert listed.json()["data"][0] == {
        "dossierId": str(service.dossier_id),
        "dossierCode": "TMI-2026-QUEUE",
        "dossierTitle": "Hồ sơ chờ phân công",
        "status": "SUBMITTED",
        "versionNo": 1,
        "submittedAt": NOW.isoformat().replace("+00:00", "Z"),
        "assignmentCount": 0,
    }
    assert listed.json()["meta"]["total"] == 1
    assert service.status is DossierStatus.SUBMITTED
    assert detail.status_code == 200
    assert detail.json()["data"]["canonicalHash"] == "a" * 64
    assert detail.json()["data"]["snapshotJson"]["evidences"] == []
