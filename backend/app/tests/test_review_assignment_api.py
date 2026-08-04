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
from app.modules.reviews.errors import ReviewConflictError
from app.modules.reviews.models import ReviewAssignmentStatus
from app.modules.reviews.types import ReviewAssignmentView

NOW = datetime(2026, 8, 1, 8, 0, tzinfo=UTC)


class StubReviewService:
    def __init__(self) -> None:
        self.dossier_id = uuid4()
        self.reviewer_ids: tuple[UUID, ...] = ()
        self.due_at: datetime | None = None
        self.conflict = False

    async def assign_reviewers(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reviewer_user_ids: tuple[UUID, ...],
        due_at: datetime | None,
    ) -> tuple[ReviewAssignmentView, ...]:
        if self.conflict:
            raise ReviewConflictError("Duplicate active assignment.")
        self.reviewer_ids = reviewer_user_ids
        self.due_at = due_at
        return tuple(
            ReviewAssignmentView(
                id=uuid4(),
                dossier_id=dossier_id,
                dossier_version_id=uuid4(),
                reviewer_user_id=reviewer_id,
                assigned_by=principal.user_id,
                due_at=due_at,
                status=ReviewAssignmentStatus.ASSIGNED,
                conflict_declared_at=None,
                conflict_reason=None,
            )
            for reviewer_id in reviewer_user_ids
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="admin@tmigroup.vn",
        roles=("SUPER_ADMIN",),
    )


async def _request(
    service: StubReviewService,
    *,
    json: dict[str, object],
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
            return await client.post(
                f"/api/v1/admin/dossiers/{service.dossier_id}/assign-reviewers",
                json=json,
            )


def test_assign_reviewers_api_contract_and_validation() -> None:
    reviewer_ids = (uuid4(), uuid4())
    service = StubReviewService()

    assigned = asyncio.run(
        _request(
            service,
            json={
                "reviewerUserIds": [str(item) for item in reviewer_ids],
                "dueAt": NOW.isoformat(),
            },
        )
    )
    invalid = asyncio.run(
        _request(
            service,
            json={"reviewerUserIds": [], "dueAt": None},
        )
    )

    assert assigned.status_code == 201
    assert len(assigned.json()["data"]) == 2
    assert assigned.json()["data"][0]["status"] == "ASSIGNED"
    assert service.reviewer_ids == reviewer_ids
    assert service.due_at == NOW
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_assign_reviewers_api_preserves_conflict_error() -> None:
    service = StubReviewService()
    service.conflict = True
    response = asyncio.run(
        _request(
            service,
            json={"reviewerUserIds": [str(uuid4())], "dueAt": None},
        )
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REVIEW_CONFLICT"
