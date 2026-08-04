import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.search.history_dependencies import get_search_history_service
from app.modules.search.history_types import SearchHistoryItem, SearchHistoryState


class StubSearchHistoryService:
    def __init__(self) -> None:
        self.user_id: UUID | None = None
        self.enabled = False
        self.recorded_query: str | None = None
        self.cleared = False

    async def get(self, user_id: UUID) -> SearchHistoryState:
        self.user_id = user_id
        items = (
            (
                SearchHistoryItem(
                    id=uuid4(),
                    display_query="Sơn mài",
                    searched_at=datetime(2026, 8, 1, tzinfo=UTC),
                ),
            )
            if self.enabled
            else ()
        )
        return SearchHistoryState(is_enabled=self.enabled, items=items)

    async def set_consent(self, user_id: UUID, *, enabled: bool) -> SearchHistoryState:
        self.user_id = user_id
        self.enabled = enabled
        return await self.get(user_id)

    async def record(self, user_id: UUID, query: str) -> bool:
        self.user_id = user_id
        self.recorded_query = query
        return self.enabled

    async def clear(self, user_id: UUID) -> int:
        self.user_id = user_id
        self.cleared = True
        return 1


async def _request(
    method: str,
    path: str,
    service: StubSearchHistoryService,
    *,
    json: dict[str, object] | None = None,
    expect_service_call: bool = True,
) -> httpx.Response:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("PUBLIC_USER",),
    )
    app = create_application(health_service=HealthService({}))
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    app.dependency_overrides[get_search_history_service] = lambda: service
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.request(method, path, json=json)
    if expect_service_call:
        assert service.user_id == principal.user_id
    return response


def test_search_history_api_consent_list_record_and_clear_contract() -> None:
    service = StubSearchHistoryService()
    disabled = asyncio.run(_request("GET", "/api/v1/me/search-history", service))
    enabled = asyncio.run(
        _request(
            "PUT",
            "/api/v1/me/search-history",
            service,
            json={"isEnabled": True},
        )
    )
    recorded = asyncio.run(
        _request(
            "POST",
            "/api/v1/me/search-history",
            service,
            json={"query": "Sơn mài"},
        )
    )
    cleared = asyncio.run(_request("DELETE", "/api/v1/me/search-history", service))

    assert disabled.status_code == 200
    assert disabled.json()["data"] == {"isEnabled": False, "items": []}
    assert enabled.json()["data"]["isEnabled"] is True
    assert set(enabled.json()["data"]["items"][0]) == {
        "id",
        "displayQuery",
        "searchedAt",
    }
    assert recorded.status_code == 200
    assert recorded.json()["data"] == {"recorded": True}
    assert service.recorded_query == "Sơn mài"
    assert cleared.status_code == 204
    assert service.cleared is True


def test_search_history_api_rejects_unknown_and_invalid_fields() -> None:
    service = StubSearchHistoryService()
    unknown = asyncio.run(
        _request(
            "PUT",
            "/api/v1/me/search-history",
            service,
            json={"isEnabled": True, "tracking": True},
            expect_service_call=False,
        )
    )
    too_long = asyncio.run(
        _request(
            "POST",
            "/api/v1/me/search-history",
            service,
            json={"query": "x" * 201},
            expect_service_call=False,
        )
    )

    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "VALIDATION_ERROR"
    assert too_long.status_code == 422
    assert too_long.json()["error"]["code"] == "VALIDATION_ERROR"
    assert service.recorded_query is None
