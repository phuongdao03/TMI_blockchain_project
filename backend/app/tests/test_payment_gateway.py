import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime

import pytest

from app.modules.payments.gateway import (
    InvalidWebhookError,
    MockPaymentGateway,
)


def test_mock_gateway_verifies_raw_body_signature() -> None:
    async def exercise() -> None:
        gateway = MockPaymentGateway(webhook_secret="test-secret")
        timestamp = 1_785_484_800
        body = json.dumps(
            {
                "event_id": "evt-1",
                "event_type": "payment.paid",
                "provider_order_id": "mock-order-1",
                "amount_minor": 1_000_000,
                "currency": "VND",
            },
            separators=(",", ":"),
        ).encode()
        signature = hmac.new(
            b"test-secret",
            str(timestamp).encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()

        event = gateway.verify_webhook(
            raw_body=body,
            signature=signature,
            timestamp=timestamp,
            now=datetime.fromtimestamp(timestamp, UTC),
        )

        assert event.provider_event_id == "evt-1"
        assert event.amount_minor == 1_000_000
        assert event.currency == "VND"

    asyncio.run(exercise())


def test_mock_gateway_rejects_tampered_raw_body() -> None:
    gateway = MockPaymentGateway(webhook_secret="test-secret")
    timestamp = 1_785_484_800

    with pytest.raises(InvalidWebhookError):
        gateway.verify_webhook(
            raw_body=b'{"event_id":"tampered"}',
            signature="0" * 64,
            timestamp=timestamp,
            now=datetime.fromtimestamp(timestamp, UTC),
        )
