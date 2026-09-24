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
from app.modules.reviews.dependencies import get_review_service
from app.modules.reviews.models import ReviewAssistanceRequestStatus
from app.modules.reviews.types import ReviewAssistanceRequestView

NOW = datetime(2026, 9, 21, 8, 0, tzinfo=UTC)


class StubReviewService:
    def __init__(self) -> None:
        self.assignment_id = uuid4()
        self.request_id = uuid4()
        self.reviewer_ids: tuple[UUID, ...] = ()
        self.due_at: datetime | None = None
        self.requested_reason: str | None = None
        self.decline_reason: str | None = None

    def _view(
        self,
        status: ReviewAssistanceRequestStatus = ReviewAssistanceRequestStatus.PENDING,
    ) -> ReviewAssistanceRequestView:
        return ReviewAssistanceRequestView(
            id=self.request_id,
            assignment_id=self.assignment_id,
            requested_by_user_id=uuid4(),
            requested_reviewer_count=2,
            reason="Hồ sơ nhiều chứng cứ cần thêm chuyên môn độc lập.",
            status=status,
            created_at=NOW,
            reviewed_by_user_id=uuid4() if status != "PENDING" else None,
            decision_reason=(
                "Đã cân đối nguồn lực và lịch thẩm định hiện tại."
                if status == ReviewAssistanceRequestStatus.DECLINED
                else None
            ),
            reviewed_at=NOW if status != "PENDING" else None,
        )

    async def request_assistance(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
        *,
        reason: str,
        requested_reviewer_count: int,
    ) -> ReviewAssistanceRequestView:
        assert assignment_id == self.assignment_id
        assert principal.roles == ("MODERATOR",)
        self.requested_reason = reason
        assert requested_reviewer_count == 2
        return self._view()

    async def approve_assistance_request(
        self,
        principal: AuthPrincipal,
        request_id: UUID,
        *,
        reviewer_user_ids: tuple[UUID, ...],
        due_at: datetime | None,
    ) -> ReviewAssistanceRequestView:
        assert request_id == self.request_id
        assert principal.roles == ("SUPER_ADMIN",)
        self.reviewer_ids = reviewer_user_ids
        self.due_at = due_at
        return self._view(ReviewAssistanceRequestStatus.APPROVED)

    async def decline_assistance_request(
        self,
        principal: AuthPrincipal,
        request_id: UUID,
        *,
        reason: str,
    ) -> ReviewAssistanceRequestView:
        assert request_id == self.request_id
        assert principal.roles == ("SUPER_ADMIN",)
        self.decline_reason = reason
        return self._view(ReviewAssistanceRequestStatus.DECLINED)


def _principal(role: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email=f"{role.lower()}@cns.vn",
        roles=(role,),
    )


async def _request(
    service: StubReviewService,
    method: str,
    path: str,
    *,
    role: str,
    json: dict[str, object],
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    principal = _principal(role)
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


def test_assistance_request_and_admin_resolution_contracts() -> None:
    async def exercise() -> None:
        service = StubReviewService()
        reviewer_ids = (uuid4(), uuid4())

        created = await _request(
            service,
            "POST",
            f"/api/v1/reviewer/assignments/{service.assignment_id}/assistance-requests",
            role="MODERATOR",
            json={
                "reason": "Hồ sơ nhiều chứng cứ cần thêm chuyên môn độc lập.",
                "requestedReviewerCount": 2,
            },
        )
        approved = await _request(
            service,
            "POST",
            f"/api/v1/admin/review-assistance-requests/{service.request_id}/approve",
            role="SUPER_ADMIN",
            json={
                "reviewerUserIds": [str(item) for item in reviewer_ids],
                "dueAt": NOW.isoformat(),
            },
        )
        declined = await _request(
            service,
            "POST",
            f"/api/v1/admin/review-assistance-requests/{service.request_id}/decline",
            role="SUPER_ADMIN",
            json={"reason": "Đã cân đối nguồn lực và lịch thẩm định hiện tại."},
        )

        assert created.status_code == 201
        assert created.json()["data"]["requestedReviewerCount"] == 2
        assert service.requested_reason is not None
        assert approved.status_code == 200
        assert approved.json()["data"]["status"] == "APPROVED"
        assert service.reviewer_ids == reviewer_ids
        assert service.due_at == NOW
        assert declined.status_code == 200
        assert declined.json()["data"]["status"] == "DECLINED"
        assert service.decline_reason is not None

    asyncio.run(exercise())


def test_assistance_request_rejects_short_reason_and_duplicate_reviewers() -> None:
    async def exercise() -> None:
        service = StubReviewService()
        invalid_request = await _request(
            service,
            "POST",
            f"/api/v1/reviewer/assignments/{service.assignment_id}/assistance-requests",
            role="MODERATOR",
            json={"reason": "too short", "requestedReviewerCount": 2},
        )
        duplicate_id = uuid4()
        invalid_approval = await _request(
            service,
            "POST",
            f"/api/v1/admin/review-assistance-requests/{service.request_id}/approve",
            role="SUPER_ADMIN",
            json={
                "reviewerUserIds": [str(duplicate_id), str(duplicate_id)],
                "dueAt": None,
            },
        )

        assert invalid_request.status_code == 422
        assert invalid_approval.status_code == 422

    asyncio.run(exercise())
