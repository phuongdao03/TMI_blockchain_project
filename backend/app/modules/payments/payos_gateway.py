import asyncio
import hashlib
import hmac
import json
import secrets
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.modules.payments.gateway import (
    InvalidWebhookError,
    PaymentGatewayError,
    ProviderOrder,
    VerifiedPaymentEvent,
)

_PAYOS_CHECKOUT_HOST = "pay.payos.vn"
_PAYOS_SUCCESS_CODE = "00"
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_KNOWN_STATUSES = frozenset({"PENDING", "PROCESSING", "PAID", "CANCELLED"})


def _encoded_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _canonical_data(data: Mapping[str, object]) -> bytes:
    return "&".join(
        f"{key}={_encoded_value(data[key])}" for key in sorted(data)
    ).encode()


class PayOSGateway:
    def __init__(
        self,
        *,
        client_id: str,
        api_key: str,
        checksum_key: str,
        return_url: str,
        cancel_url: str,
        base_url: str = "https://api-merchant.payos.vn",
        timeout_seconds: float = 8.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not all((client_id, api_key, checksum_key)):
            raise RuntimeError("payOS credentials are not configured.")
        if not return_url.startswith("https://") or not cancel_url.startswith("https://"):
            raise RuntimeError("payOS callback URLs must use HTTPS.")
        self._checksum_key = checksum_key.encode()
        self._return_url = return_url
        self._cancel_url = cancel_url
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"x-client-id": client_id, "x-api-key": api_key},
            timeout=httpx.Timeout(timeout_seconds),
        )
        if client is not None:
            self._client.headers.update(
                {"x-client-id": client_id, "x-api-key": api_key}
            )

    async def create_order(
        self,
        *,
        order_code: str,
        amount_minor: int,
        currency: str,
        expires_at: datetime,
    ) -> ProviderOrder:
        if not order_code.isdigit() or not 0 < int(order_code) <= 2_147_483_647:
            raise PaymentGatewayError("Payment order code is invalid.")
        if amount_minor <= 0 or currency.upper() != "VND":
            raise PaymentGatewayError("Payment amount or currency is invalid.")
        description = f"TMI {order_code}"
        signed_data: dict[str, object] = {
            "amount": amount_minor,
            "cancelUrl": self._cancel_url,
            "description": description,
            "orderCode": int(order_code),
            "returnUrl": self._return_url,
        }
        payload = {
            **signed_data,
            "expiredAt": int(expires_at.timestamp()),
            "signature": self._sign(signed_data),
        }
        response = await self._request(
            "POST",
            "/v2/payment-requests",
            json=payload,
            safe_to_retry=False,
        )
        data = self._verified_response_data(response)
        if data.get("orderCode") != int(order_code):
            raise PaymentGatewayError("payOS returned a mismatched order code.")
        if data.get("amount") != amount_minor or data.get("currency") != "VND":
            raise PaymentGatewayError("payOS returned a mismatched payment amount.")
        return self._provider_order(data, expect_checkout=True)

    async def get_order(self, provider_order_id: str) -> ProviderOrder:
        self._validate_identifier(provider_order_id)
        response = await self._request(
            "GET",
            f"/v2/payment-requests/{provider_order_id}",
            safe_to_retry=True,
        )
        return self._provider_order(
            self._verified_response_data(response),
            fallback_id=provider_order_id,
        )

    async def cancel_order(
        self,
        provider_order_id: str,
        *,
        reason: str,
    ) -> ProviderOrder:
        self._validate_identifier(provider_order_id)
        normalized_reason = reason.strip()
        if not normalized_reason or len(normalized_reason) > 255:
            raise PaymentGatewayError("Payment cancellation reason is invalid.")
        response = await self._request(
            "POST",
            f"/v2/payment-requests/{provider_order_id}/cancel",
            json={"cancellationReason": normalized_reason},
            safe_to_retry=False,
        )
        return self._provider_order(
            self._verified_response_data(response),
            fallback_id=provider_order_id,
        )

    def verify_webhook(
        self,
        *,
        raw_body: bytes,
        signature: str,
        timestamp: int,
        now: datetime,
    ) -> VerifiedPaymentEvent:
        del signature, timestamp, now
        try:
            payload = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidWebhookError("payOS webhook payload is invalid.") from exc
        if not isinstance(payload, dict):
            raise InvalidWebhookError("payOS webhook payload is invalid.")
        data = payload.get("data")
        body_signature = payload.get("signature")
        if not isinstance(data, dict) or not isinstance(body_signature, str):
            raise InvalidWebhookError("payOS webhook payload is invalid.")
        if not secrets.compare_digest(
            self._sign(data).lower(),
            body_signature.lower(),
        ):
            raise InvalidWebhookError("payOS webhook signature is invalid.")
        order_code = data.get("orderCode")
        amount = data.get("amount")
        currency = data.get("currency")
        provider_order_id = data.get("paymentLinkId")
        reference = data.get("reference")
        if (
            not isinstance(order_code, int)
            or isinstance(order_code, bool)
            or order_code <= 0
            or not isinstance(amount, int)
            or isinstance(amount, bool)
            or amount <= 0
            or currency != "VND"
            or not isinstance(provider_order_id, str)
            or not provider_order_id
            or len(provider_order_id) > 128
            or not isinstance(reference, str)
            or not reference
            or len(reference) > 128
        ):
            raise InvalidWebhookError("payOS webhook payment data is invalid.")
        if (
            payload.get("success") is not True
            or data.get("code") != _PAYOS_SUCCESS_CODE
        ):
            raise InvalidWebhookError("payOS webhook does not confirm payment.")
        return VerifiedPaymentEvent(
            provider_event_id=f"payos:{reference}",
            event_type="payment.paid",
            provider_order_id=provider_order_id,
            amount_minor=amount,
            currency="VND",
            order_code=str(order_code),
            payload_redacted={
                "reference": reference,
                "payment_link_id": provider_order_id,
                "order_code": str(order_code),
                "amount": amount,
                "currency": "VND",
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, object] | None = None,
        safe_to_retry: bool,
    ) -> httpx.Response:
        attempts = 2 if safe_to_retry else 1
        for attempt in range(attempts):
            try:
                response = await self._client.request(method, path, json=json)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt + 1 < attempts:
                    await asyncio.sleep(0)
                    continue
                raise PaymentGatewayError("payOS is temporarily unavailable.") from exc
            if (
                response.status_code in _RETRYABLE_STATUS_CODES
                and attempt + 1 < attempts
            ):
                await asyncio.sleep(0)
                continue
            if response.status_code != 200:
                raise PaymentGatewayError("payOS rejected the payment request.")
            return response
        raise PaymentGatewayError("payOS is temporarily unavailable.")

    def _verified_response_data(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PaymentGatewayError("payOS returned an invalid response.") from exc
        if not isinstance(payload, dict) or payload.get("code") != _PAYOS_SUCCESS_CODE:
            raise PaymentGatewayError("payOS returned an unsuccessful response.")
        data = payload.get("data")
        signature = payload.get("signature")
        if not isinstance(data, dict) or not isinstance(signature, str):
            raise PaymentGatewayError("payOS returned an invalid response.")
        expected = self._sign(data)
        if not secrets.compare_digest(expected.lower(), signature.lower()):
            raise PaymentGatewayError("payOS response signature is invalid.")
        return data

    def _provider_order(
        self,
        data: Mapping[str, object],
        *,
        expect_checkout: bool = False,
        fallback_id: str | None = None,
    ) -> ProviderOrder:
        provider_id = data.get("paymentLinkId") or data.get("id") or fallback_id
        status = data.get("status")
        order_code = data.get("orderCode")
        amount = data.get("amount")
        if (
            not isinstance(provider_id, str)
            or not provider_id
            or len(provider_id) > 128
        ):
            raise PaymentGatewayError("payOS returned an invalid payment identifier.")
        if not isinstance(status, str) or status not in _KNOWN_STATUSES:
            raise PaymentGatewayError("payOS returned an invalid payment status.")
        if (
            not isinstance(order_code, int)
            or isinstance(order_code, bool)
            or order_code <= 0
        ):
            raise PaymentGatewayError("payOS returned an invalid order code.")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise PaymentGatewayError("payOS returned an invalid payment amount.")
        checkout_url = data.get("checkoutUrl")
        qr_payload = data.get("qrCode")
        if expect_checkout:
            if not isinstance(checkout_url, str) or (
                urlparse(checkout_url).scheme != "https"
                or urlparse(checkout_url).hostname != _PAYOS_CHECKOUT_HOST
            ):
                raise PaymentGatewayError("payOS returned an invalid checkout URL.")
            if not isinstance(qr_payload, str) or not qr_payload:
                raise PaymentGatewayError("payOS returned an invalid QR payload.")
        return ProviderOrder(
            provider_order_id=provider_id,
            checkout_url=checkout_url if isinstance(checkout_url, str) else None,
            qr_payload=qr_payload if isinstance(qr_payload, str) else None,
            status=status,
            order_code=str(order_code),
            amount_minor=amount,
            currency=(
                currency.upper()
                if isinstance((currency := data.get("currency")), str)
                else None
            ),
        )

    def _sign(self, data: Mapping[str, object]) -> str:
        return hmac.new(
            self._checksum_key,
            _canonical_data(data),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _validate_identifier(value: str) -> None:
        if not value or len(value) > 128 or any(char.isspace() for char in value):
            raise PaymentGatewayError("Payment identifier is invalid.")

    async def close(self) -> None:
        await self._client.aclose()
