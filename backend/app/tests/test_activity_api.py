from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.engagement.activity import ActivityKind
from app.modules.engagement.activity_repository import ActivityListRow
from app.modules.engagement.dependencies import get_activity_service

USER_ID = UUID("50000000-0000-0000-0000-000000000021")


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=USER_ID,
        session_id=uuid4(),
        email="member@example.test",
        roles=("MEMBER",),
    )


class StubActivityService:
    async def list_for_user(
        self,
        principal: AuthPrincipal,
        *,
        cursor: str | None,
        limit: int,
    ) -> tuple[tuple[ActivityListRow, ...], str | None]:
        assert principal.user_id == USER_ID
        assert cursor == "cursor-1"
        assert limit == 10
        return (
            (
                ActivityListRow(
                    activity_id=uuid4(),
                    kind=ActivityKind.FAVORITE,
                    public_work_id=uuid4(),
                    slug="public-work",
                    title="Public work",
                    short_description="A public work.",
                    channel=None,
                    created_at=datetime.now(UTC),
                ),
            ),
            "cursor-2",
        )


def test_activity_api_is_private_and_cursor_paginated() -> None:
    app = create_application()
    app.dependency_overrides[get_activity_service] = StubActivityService
    app.dependency_overrides[get_current_principal] = _principal
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/me/activity?cursor=cursor-1&pageSize=10")
        assert response.status_code == 200
        assert response.json()["data"]["items"][0]["kind"] == "FAVORITE"
        assert response.json()["data"]["nextCursor"] == "cursor-2"
    finally:
        app.dependency_overrides.clear()
