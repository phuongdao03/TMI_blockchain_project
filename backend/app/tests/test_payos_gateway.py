import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.modules.payments.gateway import InvalidWebhookError, PaymentGatewayError
from app.modules.payments.payos_gateway import PayOSGateway

CHECKSUM = "checksum-secret"
NOW = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)


def _signature(data: dict[str, Any]) -> str:
    values: list[str] = []
    for key in sorted(data):
        value = data[key]
        if value is None:
            encoded = ""
        elif isinstance(value, bool):
            encoded = "true" if value else "false"
        elif isinstance(value, (dict, list)):
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            encoded = str(value)
        values.append(f"{key}={encoded}")
    return hmac.new(
        CHECKSUM.encode(),
        "&".join(values).encode(),
        hashlib.sha256,
    ).hexdigest()


def _response(data: dict[str, Any], *, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        json={
            "code": "00",
            "desc": "success",
            "data": data,
            "signature": _signature(data),
        },
    )


def _gateway(handler: httpx.MockTransport) -> PayOSGateway:
    return PayOSGateway(
        client_id="client-id",
        api_key="api-key",
        checksum_key=CHECKSUM,
        return_url="https://app.example/payments/return",
        cancel_url="https://app.example/payments/cancel",
        client=httpx.AsyncClient(
            transport=handler, base_url="https://api-merchant.payos.vn"
        ),
    )


def test_payos_topup_codes_and_currency_in_signed_lookup_response() -> None:
    async def exercise() -> None:
        code = 2_147_483_650
        identifier = "124c33293c934a85be5b7f8761a27a07"

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                assert json.loads(request.content)["orderCode"] == code
                return _response(
                    {
                        "paymentLinkId": identifier,
                        "orderCode": code,
                        "amount": 5000,
                        "currency": "VND",
                        "status": "PENDING",
                        "checkoutUrl": f"https://pay.payos.vn/web/{identifier}",
                        "qrCode": "verified-qr-payload",
                    }
                )
            # The documented GET response has no currency field.
            return _response(
                {
                    "id": identifier,
                    "orderCode": code,
                    "amount": 5000,
                    "amountPaid": 5000,
                    "amountRemaining": 0,
                    "status": "PAID",
                }
            )

        gateway = _gateway(httpx.MockTransport(handler))
        try:
            created = await gateway.create_order(
                order_code=str(code), amount_minor=5000, currency="VND", expires_at=NOW
            )
            assert created.order_code == str(code)
            confirmed = await gateway.get_order(identifier)
            assert confirmed.currency == "VND"
            assert confirmed.amount_minor == 5000
        finally:
            await gateway.close()

    asyncio.run(exercise())


def test_payos_create_order_signs_and_validates_response() -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["x-client-id"] == "client-id"
            assert request.headers["x-api-key"] == "api-key"
            payload = json.loads(request.content)
            signed = {
                key: payload[key]
                for key in (
                    "amount",
                    "cancelUrl",
                    "description",
                    "orderCode",
                    "returnUrl",
                )
            }
            assert payload["signature"] == _signature(signed)
            return _response(
                {
                    "paymentLinkId": "payos-link-1",
                    "orderCode": 123456,
                    "amount": 10_000,
                    "currency": "VND",
                    "status": "PENDING",
                    "checkoutUrl": "https://pay.payos.vn/web/payos-link-1",
                    "qrCode": "vietqr-payload",
                    "bin": "970422",
                    "accountNumber": "0123456789",
                    "accountName": "TINH HOA VIET",
                    "description": "CNS 123456",
                }
            )

        gateway = _gateway(httpx.MockTransport(handler))
        order = await gateway.create_order(
            order_code="123456",
            amount_minor=10_000,
            currency="VND",
            expires_at=NOW,
        )

        assert order.provider_order_id == "payos-link-1"
        assert order.checkout_url == "https://pay.payos.vn/web/payos-link-1"
        assert order.qr_payload == "vietqr-payload"
        assert order.bank_bin == "970422"
        assert order.bank_account_number == "0123456789"
        assert order.bank_account_name == "TINH HOA VIET"
        assert order.transfer_description == "CNS 123456"
        await gateway.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("status", [401, 429])
def test_payos_create_order_maps_http_failures_without_retry(status: int) -> None:
    async def exercise() -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(
                status,
                json={"code": "error", "desc": "provider failure"},
            )

        gateway = _gateway(httpx.MockTransport(handler))
        with pytest.raises(PaymentGatewayError):
            await gateway.create_order(
                order_code="123456",
                amount_minor=10_000,
                currency="VND",
                expires_at=NOW,
            )
        assert calls == 1
        await gateway.close()

    asyncio.run(exercise())


def test_payos_create_order_maps_timeout() -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timeout", request=request)

        gateway = _gateway(httpx.MockTransport(handler))
        with pytest.raises(PaymentGatewayError):
            await gateway.create_order(
                order_code="123456",
                amount_minor=10_000,
                currency="VND",
                expires_at=NOW,
            )
        await gateway.close()

    asyncio.run(exercise())


def test_payos_create_timeout_recovers_existing_link_by_order_code() -> None:
    async def exercise() -> None:
        requests: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append((request.method, request.url.path))
            if request.method == "POST":
                raise httpx.ReadTimeout("response lost", request=request)
            assert request.url.path == "/v2/payment-requests/123456"
            return _response(
                {
                    "id": "payos-link-1",
                    "orderCode": 123456,
                    "amount": 10_000,
                    "status": "PENDING",
                }
            )

        gateway = _gateway(httpx.MockTransport(handler))
        recovered = await gateway.create_order(
            order_code="123456",
            amount_minor=10_000,
            currency="VND",
            expires_at=NOW,
        )
        assert recovered.provider_order_id == "payos-link-1"
        assert recovered.checkout_url == "https://pay.payos.vn/web/payos-link-1"
        assert requests == [
            ("POST", "/v2/payment-requests"),
            ("GET", "/v2/payment-requests/123456"),
        ]
        await gateway.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "data",
    [
        {"paymentLinkId": "payos-link-1"},
        {
            "paymentLinkId": "payos-link-1",
            "orderCode": 999999,
            "amount": 10_000,
            "currency": "VND",
            "status": "PENDING",
            "checkoutUrl": "https://pay.payos.vn/web/payos-link-1",
            "qrCode": "vietqr-payload",
        },
        {
            "paymentLinkId": "payos-link-1",
            "orderCode": 123456,
            "amount": 99_999,
            "currency": "VND",
            "status": "PENDING",
            "checkoutUrl": "https://pay.payos.vn/web/payos-link-1",
            "qrCode": "vietqr-payload",
        },
    ],
)
def test_payos_create_order_rejects_malformed_or_mismatched_data(
    data: dict[str, Any],
) -> None:
    async def exercise() -> None:
        gateway = _gateway(httpx.MockTransport(lambda request: _response(data)))
        with pytest.raises(PaymentGatewayError):
            await gateway.create_order(
                order_code="123456",
                amount_minor=10_000,
                currency="VND",
                expires_at=NOW,
            )
        await gateway.close()

    asyncio.run(exercise())


def test_payos_lookup_retries_rate_limit_and_maps_status() -> None:
    async def exercise() -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(429, json={"code": "too_many_requests"})
            return _response(
                {
                    "id": "payos-link-1",
                    "orderCode": 123456,
                    "amount": 10_000,
                    "amountPaid": 10_000,
                    "amountRemaining": 0,
                    "status": "PAID",
                    "createdAt": "2026-08-08T08:00:00.000Z",
                    "transactions": [],
                }
            )

        gateway = _gateway(httpx.MockTransport(handler))
        order = await gateway.get_order("payos-link-1")
        assert order.status == "PAID"
        assert order.order_code == "123456"
        assert order.amount_minor == 10_000
        assert calls == 2
        await gateway.close()

    asyncio.run(exercise())


def test_payos_cancel_uses_provider_identifier_and_reason() -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v2/payment-requests/payos-link-1/cancel"
            assert json.loads(request.content) == {
                "cancellationReason": "Applicant cancelled checkout"
            }
            return _response(
                {
                    "id": "payos-link-1",
                    "orderCode": 123456,
                    "amount": 10_000,
                    "amountPaid": 0,
                    "amountRemaining": 10_000,
                    "status": "CANCELLED",
                    "createdAt": "2026-08-08T08:00:00.000Z",
                    "transactions": [],
                }
            )

        gateway = _gateway(httpx.MockTransport(handler))
        order = await gateway.cancel_order(
            "payos-link-1",
            reason="Applicant cancelled checkout",
        )
        assert order.status == "CANCELLED"
        await gateway.close()

    asyncio.run(exercise())


def test_payos_rejects_invalid_response_signature() -> None:
    async def exercise() -> None:
        data = {
            "paymentLinkId": "payos-link-1",
            "orderCode": 123456,
            "amount": 10_000,
            "currency": "VND",
            "status": "PENDING",
            "checkoutUrl": "https://pay.payos.vn/web/payos-link-1",
            "qrCode": "vietqr-payload",
        }
        gateway = _gateway(
            httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "code": "00",
                        "desc": "success",
                        "data": data,
                        "signature": "0" * 64,
                    },
                )
            )
        )
        with pytest.raises(PaymentGatewayError):
            await gateway.create_order(
                order_code="123456",
                amount_minor=10_000,
                currency="VND",
                expires_at=NOW,
            )
        await gateway.close()

    asyncio.run(exercise())


def test_payos_verifies_webhook_body_before_returning_redacted_event() -> None:
    data = {
        "orderCode": 123456,
        "amount": 10_000,
        "description": "CNS 123456",
        "accountNumber": "private-account",
        "reference": "bank-reference-1",
        "transactionDateTime": "2026-08-08 08:00:00",
        "currency": "VND",
        "paymentLinkId": "payos-link-1",
        "code": "00",
        "desc": "Thành công",
    }
    body = json.dumps(
        {
            "code": "00",
            "desc": "success",
            "success": True,
            "data": data,
            "signature": _signature(data),
        }
    ).encode()
    gateway = _gateway(httpx.MockTransport(lambda request: httpx.Response(500)))

    event = gateway.verify_webhook(
        raw_body=body,
        signature="",
        timestamp=0,
        now=NOW,
    )

    assert event.provider_event_id == "payos:bank-reference-1"
    assert event.provider_order_id == "payos-link-1"
    assert event.order_code == "123456"
    assert "accountNumber" not in event.payload_redacted


def test_payos_rejects_tampered_webhook() -> None:
    gateway = _gateway(httpx.MockTransport(lambda request: httpx.Response(500)))
    body = json.dumps(
        {
            "code": "00",
            "desc": "success",
            "success": True,
            "data": {"orderCode": 123456, "amount": 99_999},
            "signature": "0" * 64,
        }
    ).encode()

    with pytest.raises(InvalidWebhookError):
        gateway.verify_webhook(
            raw_body=body,
            signature="",
            timestamp=0,
            now=NOW,
        )
