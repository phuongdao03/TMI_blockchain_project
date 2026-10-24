import asyncio
from uuid import uuid4

import httpx

from app.core.config import Settings, get_settings
from app.core.health import HealthService
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.auth.tokens import CsrfTokenManager
from app.modules.payments.dependencies import get_payment_service
from app.tests.test_payment_service import _service, _webhook


def test_wallet_http_contract_csrf_verified_funding_and_ownership() -> None:
    async def exercise() -> None:
        payment, _, engine, owner = await _service()
        principal = [owner]
        secret = "wallet-test-csrf-secret-32-characters-safe"
        settings = Settings.model_validate(
            {"app_env": "local", "auth_csrf_secret": secret}
        )
        csrf = CsrfTokenManager(secret=secret).issue(owner.session_id)
        app = create_application(settings=settings, health_service=HealthService({}))
        app.dependency_overrides[get_payment_service] = lambda: payment
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_current_principal] = lambda: principal[0]

        async def test_session():
            yield payment._session

        app.dependency_overrides[get_session] = test_session
        try:
            async with (
                app.router.lifespan_context(app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://testserver",
                    cookies={"cns_csrf": csrf},
                ) as client,
            ):
                response = await client.get("/api/v1/wallet")
                assert response.status_code == 200
                assert response.json()["data"]["balanceMinor"] == 0
                assert response.headers["cache-control"] == "no-store"
                assert (
                    await client.post(
                        "/api/v1/wallet/topups",
                        json={"amountMinor": 10_000},
                        headers={"Idempotency-Key": "fund"},
                    )
                ).status_code == 403
                headers = {"Idempotency-Key": "fund", "X-CSRF-Token": csrf}
                assert (
                    await client.post(
                        "/api/v1/wallet/topups",
                        json={"amountMinor": 10_000.5},
                        headers=headers,
                    )
                ).status_code == 422
                created = await client.post(
                    "/api/v1/wallet/topups",
                    json={"amountMinor": 10_000},
                    headers=headers,
                )
                assert created.status_code == 200
                topup = created.json()["data"]
                body, signature, stamp = _webhook(
                    amount_minor=10_000, order_code=topup["orderCode"]
                )
                webhook = await client.post(
                    "/api/v1/webhooks/payments/mock",
                    content=body,
                    headers={
                        "X-Payment-Signature": signature,
                        "X-Payment-Timestamp": str(stamp),
                    },
                )
                assert webhook.status_code == 204
                assert (await client.get("/api/v1/wallet")).json()["data"][
                    "balanceMinor"
                ] == 10_000
                principal[0] = AuthPrincipal(
                    user_id=uuid4(),
                    session_id=uuid4(),
                    email="other@example.vn",
                    roles=("USER",),
                )
                csrf = CsrfTokenManager(secret=secret).issue(principal[0].session_id)
                client.cookies.set("cns_csrf", csrf)
                headers["X-CSRF-Token"] = csrf
                assert (await client.get("/api/v1/wallet")).json()["data"][
                    "balanceMinor"
                ] == 0
                assert (
                    await client.post(
                        f"/api/v1/wallet/topups/{topup['id']}/reconcile",
                        headers=headers,
                    )
                ).status_code == 404
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
