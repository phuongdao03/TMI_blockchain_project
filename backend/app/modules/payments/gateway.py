import hashlib
import hmac
import json
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4


class PaymentGatewayError(Exception):
    """Provider communication or response failure."""


class InvalidWebhookError(PaymentGatewayError):
    """Webhook authenticity, freshness, or payload validation failure."""


@dataclass(frozen=True, slots=True)
class ProviderOrder:
    provider_order_id: str
    checkout_url: str | None
    qr_payload: str | None
    status: str
    order_code: str | None = None
    amount_minor: int | None = None
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class VerifiedPaymentEvent:
    provider_event_id: str
    event_type: str
    provider_order_id: str
    amount_minor: int
    currency: str
    payload_redacted: Mapping[str, object]
    order_code: str | None = None


class PaymentGateway(Protocol):
    async def create_order(
        self,
        *,
        order_code: str,
        amount_minor: int,
        currency: str,
        expires_at: datetime,
    ) -> ProviderOrder: ...

    async def get_order(self, provider_order_id: str) -> ProviderOrder: ...

    async def cancel_order(
        self,
        provider_order_id: str,
        *,
        reason: str,
    ) -> ProviderOrder: ...

    def verify_webhook(
        self,
        *,
        raw_body: bytes,
        signature: str,
        timestamp: int,
        now: datetime,
    ) -> VerifiedPaymentEvent: ...

    async def close(self) -> None: ...


class MockPaymentGateway:
    def __init__(
        self,
        *,
        webhook_secret: str,
        checkout_base_url: str = "http://localhost:3000/thanh-toan/mock",
        uuid_factory: Callable[[], object] | None = None,
        webhook_tolerance_seconds: int = 300,
    ) -> None:
        if not webhook_secret:
            raise RuntimeError("Payment webhook secret is not configured.")
        self._secret = webhook_secret.encode()
        self._checkout_base_url = checkout_base_url.rstrip("/")
        self._uuid_factory = uuid_factory or uuid4
        self._webhook_tolerance_seconds = webhook_tolerance_seconds
        self._orders: dict[str, ProviderOrder] = {}

    async def create_order(
        self,
        *,
        order_code: str,
        amount_minor: int,
        currency: str,
        expires_at: datetime,
    ) -> ProviderOrder:
        del amount_minor, currency, expires_at
        provider_order_id = f"mock-{self._uuid_factory()}"
        order = ProviderOrder(
            provider_order_id=provider_order_id,
            checkout_url=f"{self._checkout_base_url}/{provider_order_id}",
            qr_payload=f"TMI|{order_code}|{provider_order_id}",
            status=PaymentStatusName.PENDING,
        )
        self._orders[provider_order_id] = order
        return order

    async def get_order(self, provider_order_id: str) -> ProviderOrder:
        try:
            return self._orders[provider_order_id]
        except KeyError as exc:
            raise PaymentGatewayError("Provider order was not found.") from exc

    async def cancel_order(
        self,
        provider_order_id: str,
        *,
        reason: str,
    ) -> ProviderOrder:
        del reason
        order = await self.get_order(provider_order_id)
        cancelled = ProviderOrder(
            provider_order_id=order.provider_order_id,
            checkout_url=order.checkout_url,
            qr_payload=order.qr_payload,
            status="CANCELLED",
        )
        self._orders[provider_order_id] = cancelled
        return cancelled

    def verify_webhook(
        self,
        *,
        raw_body: bytes,
        signature: str,
        timestamp: int,
        now: datetime,
    ) -> VerifiedPaymentEvent:
        normalized_now = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        if abs(int(normalized_now.timestamp()) - timestamp) > (
            self._webhook_tolerance_seconds
        ):
            raise InvalidWebhookError("Webhook timestamp is outside tolerance.")
        expected = hmac.new(
            self._secret,
            str(timestamp).encode() + b"." + raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not secrets.compare_digest(expected, signature):
            raise InvalidWebhookError("Webhook signature is invalid.")
        try:
            payload = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidWebhookError("Webhook payload is invalid.") from exc
        if not isinstance(payload, dict):
            raise InvalidWebhookError("Webhook payload is invalid.")
        event_id = self._required_string(payload, "event_id", 128)
        event_type = self._required_string(payload, "event_type", 64)
        provider_order_id = self._required_string(
            payload,
            "provider_order_id",
            128,
        )
        currency = self._required_string(payload, "currency", 3).upper()
        amount_minor = payload.get("amount_minor")
        if (
            not isinstance(amount_minor, int)
            or isinstance(amount_minor, bool)
            or amount_minor <= 0
        ):
            raise InvalidWebhookError("Webhook amount is invalid.")
        return VerifiedPaymentEvent(
            provider_event_id=event_id,
            event_type=event_type,
            provider_order_id=provider_order_id,
            amount_minor=amount_minor,
            currency=currency,
            payload_redacted={
                "event_type": event_type,
                "provider_order_id": provider_order_id,
                "amount_minor": amount_minor,
                "currency": currency,
            },
        )

    @staticmethod
    def _required_string(
        payload: Mapping[str, object],
        field: str,
        maximum: int,
    ) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value or len(value) > maximum:
            raise InvalidWebhookError(f"Webhook field {field} is invalid.")
        return value

    async def close(self) -> None:
        return None


class PaymentStatusName:
    PENDING = "PENDING"
