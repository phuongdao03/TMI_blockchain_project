import asyncio
from dataclasses import replace
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
from app.modules.reviews.dependencies import get_similarity_review_service
from app.modules.reviews.models import (
    SimilarityCaseDisposition,
    SimilarityCaseStatus,
    SimilaritySignalType,
)
from app.modules.reviews.types import (
    SimilarityAssetSummary,
    SimilarityCasePage,
    SimilarityCaseView,
)

NOW = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)


class StubSimilarityService:
    def __init__(self) -> None:
        self.case = SimilarityCaseView(
            id=uuid4(),
            left_dossier_version_id=uuid4(),
            right_dossier_version_id=uuid4(),
            left_asset=SimilarityAssetSummary(
                dossier_id=uuid4(),
                dossier_code="DOS-001",
                dossier_title="Bình minh trên sông",
                version_no=1,
                evidence_media_ids=(uuid4(),),
            ),
            right_asset=SimilarityAssetSummary(
                dossier_id=uuid4(),
                dossier_code="DOS-002",
                dossier_title="Bình minh bên sông",
                version_no=2,
                evidence_media_ids=(uuid4(),),
            ),
            signal_type=SimilaritySignalType.TEXT,
            text_score=0.91,
            image_distance=None,
            policy_version="near-duplicate-v1",
            status=SimilarityCaseStatus.OPEN,
            assigned_reviewer_user_id=None,
            disposition=None,
            resolution_reason=None,
            created_at=NOW,
            assigned_at=None,
            resolved_at=None,
        )

    async def list_reviewer_cases(
        self,
        principal: AuthPrincipal,
        *,
        status: SimilarityCaseStatus | None,
        page: int,
        page_size: int,
    ) -> SimilarityCasePage:
        assert page == 1
        assert page_size == 10
        return SimilarityCasePage(items=(self.case,), total=1)

    async def list_admin_cases(
        self,
        principal: AuthPrincipal,
        *,
        status: SimilarityCaseStatus | None,
        page: int,
        page_size: int,
    ) -> SimilarityCasePage:
        assert status is SimilarityCaseStatus.OPEN
        assert page == 1
        assert page_size == 20
        return SimilarityCasePage(items=(self.case,), total=1)

    async def assign_case(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        reviewer_user_id: UUID,
    ) -> SimilarityCaseView:
        assert case_id == self.case.id
        self.case = replace(
            self.case,
            status=SimilarityCaseStatus.ASSIGNED,
            assigned_reviewer_user_id=reviewer_user_id,
            assigned_at=NOW,
        )
        return self.case

    async def get_case(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
    ) -> SimilarityCaseView:
        assert case_id == self.case.id
        return self.case

    async def resolve_case(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        *,
        disposition: SimilarityCaseDisposition,
        reason: str,
    ) -> SimilarityCaseView:
        self.case = replace(
            self.case,
            status=SimilarityCaseStatus.RESOLVED,
            disposition=disposition,
            resolution_reason=reason,
            resolved_at=NOW,
        )
        return self.case


def _principal(*roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="internal@tmigroup.vn",
        roles=roles,
    )


async def _request(
    service: StubSimilarityService,
    principal: AuthPrincipal,
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_similarity_review_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_admin_assignment_and_reviewer_resolution_contracts_use_english_paths() -> None:
    async def exercise() -> None:
        service = StubSimilarityService()
        reviewer_id = uuid4()
        admin_list = await _request(
            service,
            _principal("SUPER_ADMIN"),
            "GET",
            "/api/v1/admin/similarity-cases?status=OPEN&page=1&pageSize=20",
        )
        assert admin_list.status_code == 200
        assert admin_list.json()["meta"]["total"] == 1
        assert admin_list.json()["data"][0]["leftAsset"]["dossierCode"] == "DOS-001"
        assigned = await _request(
            service,
            _principal("SUPER_ADMIN"),
            "POST",
            f"/api/v1/admin/similarity-cases/{service.case.id}/assign",
            json={"reviewerUserId": str(reviewer_id)},
        )
        assert assigned.status_code == 200
        assert assigned.json()["data"]["status"] == "ASSIGNED"

        detail = await _request(
            service,
            _principal("REVIEWER"),
            "GET",
            f"/api/v1/reviewer/similarity-cases/{service.case.id}",
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["policyVersion"] == "near-duplicate-v1"

        listed = await _request(
            service,
            _principal("REVIEWER"),
            "GET",
            "/api/v1/reviewer/similarity-cases?page=1&pageSize=10",
        )
        assert listed.status_code == 200
        assert listed.json()["meta"]["total"] == 1

        resolved = await _request(
            service,
            _principal("REVIEWER"),
            "POST",
            f"/api/v1/reviewer/similarity-cases/{service.case.id}/resolve",
            json={
                "disposition": "RELATED",
                "reason": (
                    "The works belong to one series but remain separate entries."
                ),
            },
        )
        assert resolved.status_code == 200
        assert resolved.json()["data"]["disposition"] == "RELATED"

    asyncio.run(exercise())
