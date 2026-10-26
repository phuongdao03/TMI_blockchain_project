import asyncio

import httpx

from app.core.health import HealthService
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.tests.test_payment_service import ADMIN_ID, _service


def test_chat_api_pages_edits_and_moderator_removes_messages() -> None:
    async def exercise() -> None:
        payment, _, engine, owner = await _service()
        current = [owner]
        app = create_application(health_service=HealthService({}))
        app.dependency_overrides[get_csrf_protected_principal] = lambda: current[0]
        app.dependency_overrides[get_current_principal] = lambda: current[0]

        async def test_session():
            yield payment._session

        app.dependency_overrides[get_session] = test_session
        try:
            async with (
                app.router.lifespan_context(app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://testserver",
                ) as client,
            ):
                invalid_limit = await client.get(
                    "/api/v1/community/chat/MEMBER/messages?limit=101"
                )
                assert invalid_limit.status_code == 422

                created = await client.post(
                    "/api/v1/community/chat/MEMBER/messages",
                    json={"body": "Original"},
                )
                assert created.status_code == 200
                message_id = created.json()["data"]["id"]
                assert created.json()["data"]["canEdit"] is True
                assert created.json()["data"]["isAdmin"] is False

                page = await client.get(
                    "/api/v1/community/chat/MEMBER/messages?limit=1"
                )
                assert page.status_code == 200
                assert page.json()["data"]["hasMore"] is False
                assert page.json()["data"]["nextCursor"] is None
                assert page.json()["data"]["items"][0]["id"] == message_id

                edited = await client.patch(
                    f"/api/v1/community/chat/messages/{message_id}",
                    json={"body": "Updated"},
                )
                assert edited.status_code == 200
                assert edited.json()["data"]["body"] == "Updated"
                assert edited.json()["data"]["editedAt"] is not None

                current[0] = AuthPrincipal(
                    user_id=ADMIN_ID,
                    session_id=owner.session_id,
                    email="moderator@example.vn",
                    roles=(),
                    permissions=("community.moderate",),
                )
                moderator_edit = await client.patch(
                    f"/api/v1/community/chat/messages/{message_id}",
                    json={"body": "Moderator cannot edit"},
                )
                assert moderator_edit.status_code == 403

                removed = await client.delete(
                    f"/api/v1/community/chat/messages/{message_id}"
                )
                assert removed.status_code == 200
                current[0] = owner
                missing_edit = await client.patch(
                    f"/api/v1/community/chat/messages/{message_id}",
                    json={"body": "After removal"},
                )
                assert missing_edit.status_code == 404

                latest = await client.get("/api/v1/community/chat/MEMBER/messages")
                assert latest.json()["data"]["items"] == []
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
