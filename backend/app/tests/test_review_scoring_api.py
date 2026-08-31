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
from app.modules.reviews.dependencies import get_review_service
from app.modules.reviews.models import (
    ReviewAssignmentStatus,
    ReviewRecommendation,
)
from app.modules.reviews.types import (
    ReviewAssignmentDetailView,
    ReviewAssignmentPage,
    ReviewAssignmentSummaryView,
    ReviewAssignmentView,
    ReviewDraft,
    ReviewView,
)

NOW = datetime(2026, 8, 2, 8, 0, tzinfo=UTC)


class StubScoringService:
    def __init__(self) -> None:
        self.assignment = ReviewAssignmentView(
            id=uuid4(),
            dossier_id=uuid4(),
            dossier_version_id=uuid4(),
            reviewer_user_id=uuid4(),
            assigned_by=uuid4(),
            due_at=NOW,
            status=ReviewAssignmentStatus.ASSIGNED,
            conflict_declared_at=None,
            conflict_reason=None,
        )
        self.review: ReviewView | None = None
        self.received_draft: ReviewDraft | None = None

    async def list_assignments(
        self,
        principal: AuthPrincipal,
        *,
        status: ReviewAssignmentStatus | None,
        page: int,
        page_size: int,
    ) -> ReviewAssignmentPage:
        assert principal.roles == ("REVIEWER",)
        assert status is ReviewAssignmentStatus.ASSIGNED
        assert page == 2
        assert page_size == 5
        return ReviewAssignmentPage(
            items=(
                ReviewAssignmentSummaryView(
                    assignment=self.assignment,
                    dossier_code="HS-2026-000001",
                    dossier_title="Hồ sơ kiểm thử",
                    version_no=1,
                ),
            ),
            total=6,
        )

    async def get_assignment(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
    ) -> ReviewAssignmentDetailView:
        assert assignment_id == self.assignment.id
        return ReviewAssignmentDetailView(
            assignment=self.assignment,
            dossier_code="HS-2026-000001",
            dossier_title="Hồ sơ kiểm thử",
            version_no=1,
            canonical_hash=None,
            snapshot_json=None,
            review=self.review,
        )

    async def declare_conflict(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
        *,
        has_conflict: bool,
        reason: str | None,
    ) -> ReviewAssignmentView:
        assert assignment_id == self.assignment.id
        assert not has_conflict
        assert reason is None
        self.assignment = replace(
            self.assignment,
            status=ReviewAssignmentStatus.IN_PROGRESS,
            conflict_declared_at=NOW,
        )
        return self.assignment

    async def save_draft(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
        draft: ReviewDraft,
    ) -> ReviewView:
        self.received_draft = draft
        self.review = ReviewView(
            id=uuid4(),
            assignment_id=assignment_id,
            truth_score=draft.truth_score,
            transparency_score=draft.transparency_score,
            ownership_score=draft.ownership_score,
            professionalism_score=draft.professionalism_score,
            respect_score=draft.respect_score,
            total_score=80,
            rubric_version=None,
            specialist_score=None,
            recommendation=draft.recommendation,
            criterion_comments=draft.criterion_comments,
            criterion_evidence=draft.criterion_evidence,
            findings=draft.findings,
            checklist_answers=draft.checklist_answers,
            applicant_feedback=draft.applicant_feedback,
            private_note=draft.private_note,
            gate_answers=draft.gate_answers,
            specialist_answers=draft.specialist_answers,
            submitted_at=None,
        )
        return self.review

    async def submit_review(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
    ) -> ReviewView:
        assert self.review is not None
        self.review = replace(self.review, submitted_at=NOW)
        return self.review


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="reviewer@tmigroup.vn",
        roles=("REVIEWER",),
    )


async def _request(
    service: StubScoringService,
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    principal = _principal()
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_review_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_reviewer_assignment_read_contract() -> None:
    async def exercise() -> None:
        service = StubScoringService()
        listed = await _request(
            service,
            "GET",
            "/api/v1/reviewer/assignments?status=ASSIGNED&page=2&pageSize=5",
        )
        detail = await _request(
            service,
            "GET",
            f"/api/v1/reviewer/assignments/{service.assignment.id}",
        )

        assert listed.status_code == 200
        assert listed.json()["meta"]["total"] == 6
        assert listed.json()["data"][0]["dossierCode"] == "HS-2026-000001"
        assert detail.status_code == 200
        assert detail.json()["data"]["snapshotJson"] is None
        assert detail.json()["data"]["review"] is None

    asyncio.run(exercise())


def test_reviewer_conflict_draft_and_submit_contract() -> None:
    async def exercise() -> None:
        service = StubScoringService()
        base = f"/api/v1/reviewer/assignments/{service.assignment.id}"
        acknowledged = await _request(
            service,
            "POST",
            f"{base}/conflict",
            json={"hasConflict": False, "reason": None},
        )
        draft = await _request(
            service,
            "PUT",
            f"{base}/draft",
            json={
                "truthScore": 18,
                "transparencyScore": 17,
                "ownershipScore": 16,
                "professionalismScore": 15,
                "respectScore": 14,
                "criterionComments": {
                    "truth": "Đúng sự thật",
                    "transparency": "Minh bạch",
                    "ownership": "Trách nhiệm",
                    "professionalism": "Chuyên nghiệp",
                    "respect": "Tôn trọng",
                },
                "recommendation": "APPROVE",
                "privateNote": "Ghi chú nội bộ",
            },
        )
        invalid = await _request(
            service,
            "PUT",
            f"{base}/draft",
            json={"truthScore": 21},
        )
        submitted = await _request(service, "POST", f"{base}/submit")

        assert acknowledged.status_code == 200
        assert acknowledged.json()["data"]["status"] == "IN_PROGRESS"
        assert draft.status_code == 200
        assert draft.json()["data"]["totalScore"] == 80
        assert service.received_draft is not None
        assert service.received_draft.recommendation is ReviewRecommendation.APPROVE
        assert invalid.status_code == 422
        assert submitted.status_code == 200
        assert submitted.json()["data"]["submittedAt"] == "2026-08-02T08:00:00Z"

    asyncio.run(exercise())
