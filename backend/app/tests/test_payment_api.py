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
from app.modules.payments.dependencies import get_payment_service
from app.modules.payments.errors import PaymentNotFoundError
from app.modules.payments.models import PaymentStatus
from app.modules.payments.types import PaymentOrderView

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


class StubPaymentService:
    def __init__(self) -> None:
        self.order_id = uuid4()
        self.dossier_id = uuid4()
        self.raw_body: bytes | None = None

    @property
    def provider_name(self) -> str:
        return "mock"

    def view(self) -> PaymentOrderView:
        return PaymentOrderView(
            id=self.order_id,
            order_code="PAY-000001",
            dossier_id=self.dossier_id,
            provider="mock",
            provider_order_id="mock-order",
            amount_minor=1_000_000,
            currency="VND",
            status=PaymentStatus.PENDING,
            expires_at=NOW,
            paid_at=None,
            checkout_url="https://payments.example/checkout",
            qr_payload="TMI|PAY-000001",
            created_at=NOW,
            updated_at=NOW,
        )

    async def create_order(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
    ) -> PaymentOrderView:
        del principal, dossier_id, idempotency_key
        return self.view()

    async def issue_order(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
        amount_minor: int,
        currency: str,
        description: str,
        due_at: datetime | None,
    ) -> PaymentOrderView:
        del principal, dossier_id, idempotency_key
        del amount_minor, currency, description, due_at
        return self.view()

    async def get_order(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
    ) -> PaymentOrderView:
        del principal, order_id
        return self.view()

    async def get_order_by_provider_reference(
        self,
        principal: AuthPrincipal,
        provider_order_id: str,
    ) -> PaymentOrderView:
        del principal, provider_order_id
        return self.view()

    async def get_active_order_for_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> PaymentOrderView:
        del principal, dossier_id
        return self.view()

    async def process_webhook(
        self,
        *,
        raw_body: bytes,
        signature: str,
        timestamp: int,
    ) -> PaymentOrderView:
        del signature, timestamp
        self.raw_body = raw_body
        return self.view()

    async def cancel_order(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
        *,
        reason: str,
    ) -> PaymentOrderView:
        del principal, order_id, reason
        return self.view()

    async def reconcile_order(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
    ) -> PaymentOrderView:
        del principal, order_id
        return self.view()


async def _request(
    method: str,
    path: str,
    service: StubPaymentService,
    *,
    content: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_payment_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(
                method,
                path,
                content=content,
                headers=headers,
            )


def test_payment_api_create_get_and_preserve_raw_webhook_body() -> None:
    service = StubPaymentService()
    created = asyncio.run(
        _request(
            "POST",
            f"/api/v1/admin/dossiers/{service.dossier_id}/payment-orders",
            service,
            content=(
                b'{"amountMinor":1500000,"currency":"VND",'
                b'"description":"Phi xac lap va phat hanh chung thu"}'
            ),
            headers={
                "Idempotency-Key": "payment-request-1",
                "Content-Type": "application/json",
            },
        )
    )
    fetched = asyncio.run(
        _request(
            "GET",
            f"/api/v1/payment-orders/{service.order_id}",
            service,
        )
    )
    fetched_by_provider = asyncio.run(
        _request(
            "GET",
            "/api/v1/payment-orders/by-provider-reference?providerOrderId=mock-order",
            service,
        )
    )
    active = asyncio.run(
        _request(
            "GET",
            f"/api/v1/dossiers/{service.dossier_id}/active-payment-order",
            service,
        )
    )
    body = b'{"provider_order_id":"mock-order"}'
    webhook = asyncio.run(
        _request(
            "POST",
            "/api/v1/webhooks/payments/mock",
            service,
            content=body,
            headers={
                "X-Payment-Signature": "a" * 64,
                "X-Payment-Timestamp": "1785484800",
                "Content-Type": "application/json",
            },
        )
    )

    assert created.status_code == 201
    assert created.json()["data"]["amountMinor"] == 1_000_000
    assert fetched.status_code == 200
    assert fetched_by_provider.status_code == 200
    assert active.status_code == 200
    assert webhook.status_code == 200
    assert service.raw_body == body


def test_payos_webhook_acknowledges_signed_registration_probe() -> None:
    class PayOSProbeService(StubPaymentService):
        @property
        def provider_name(self) -> str:
            return "payos"

        async def process_webhook(
            self,
            *,
            raw_body: bytes,
            signature: str,
            timestamp: int,
        ) -> PaymentOrderView:
            del signature, timestamp
            self.raw_body = raw_body
            raise PaymentNotFoundError()

    service = PayOSProbeService()
    body = b'{"success":true,"data":{"orderCode":123},"signature":"signed"}'
    response = asyncio.run(
        _request(
            "POST",
            "/api/v1/webhooks/payments/payos",
            service,
            content=body,
            headers={"Content-Type": "application/json"},
        )
    )

    assert response.status_code == 204
    assert service.raw_body == body


def test_payment_api_exposes_cancel_and_finance_reconciliation_commands() -> None:
    service = StubPaymentService()
    cancelled = asyncio.run(
        _request(
            "POST",
            f"/api/v1/payment-orders/{service.order_id}/cancel",
            service,
            content=b'{"reason":"Applicant requested cancellation"}',
            headers={"Content-Type": "application/json"},
        )
    )
    reconciled = asyncio.run(
        _request(
            "POST",
            f"/api/v1/admin/payment-orders/{service.order_id}/reconcile",
            service,
        )
    )

    assert cancelled.status_code == 200
    assert reconciled.status_code == 200
