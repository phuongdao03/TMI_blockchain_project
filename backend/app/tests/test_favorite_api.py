from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.engagement.dependencies import get_favorite_service
from app.modules.engagement.favorite_repository import FavoriteListRow

USER_ID = UUID("50000000-0000-0000-0000-000000000001")
WORK_ID = UUID("50000000-0000-0000-0000-000000000002")


class StubFavoriteService:
    def __init__(self) -> None:
        self.added: list[str] = []
        self.removed: list[str] = []

    async def add(
        self,
        _principal: AuthPrincipal,
        *,
        slug: str,
        **_kwargs: object,
    ) -> bool:
        self.added.append(slug)
        return True

    async def remove(
        self,
        _principal: AuthPrincipal,
        *,
        slug: str,
        **_kwargs: object,
    ) -> bool:
        self.removed.append(slug)
        return True

    async def list_for_user(
        self,
        _principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[FavoriteListRow, ...], int]:
        assert (page, page_size) == (2, 10)
        return (
            (
                FavoriteListRow(
                    favorite_id=uuid4(),
                    public_work_id=WORK_ID,
                    slug="public-work",
                    title="Public work",
                    short_description="A public work.",
                    created_at=datetime.now(UTC),
                ),
            ),
            1,
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=USER_ID,
        session_id=uuid4(),
        email="member@example.test",
        roles=("MEMBER",),
    )


def test_favorite_api_requires_authentication_and_csrf_contracts() -> None:
    service = StubFavoriteService()
    app = create_application()
    app.dependency_overrides[get_favorite_service] = lambda: service
    app.dependency_overrides[get_current_principal] = _principal
    app.dependency_overrides[get_csrf_protected_principal] = _principal
    try:
        with TestClient(app) as client:
            added = client.put("/api/v1/public/works/public-work/favorite")
            assert added.status_code == 204
            removed = client.delete("/api/v1/public/works/public-work/favorite")
            assert removed.status_code == 204
            listed = client.get("/api/v1/me/favorites?page=2&pageSize=10")
            assert listed.status_code == 200
            assert listed.json()["meta"]["total"] == 1
            assert listed.json()["data"][0]["publicWorkId"] == str(WORK_ID)
    finally:
        app.dependency_overrides.clear()

    assert service.added == ["public-work"]
    assert service.removed == ["public-work"]
