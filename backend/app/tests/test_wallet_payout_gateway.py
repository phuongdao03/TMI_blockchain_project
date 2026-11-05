import asyncio
import json

import httpx
import pytest

from app.modules.wallet.payout_gateway import (
    PayOSPayoutGateway,
    PayoutOutcomeUnknown,
    payout_signature,
)


def test_payout_gateway_signs_and_submits_only_to_mock_transport() -> None:
    async def exercise() -> None:
        requests: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            body = json.loads(request.content)
            assert request.url.path == "/v1/payouts"
            assert request.headers["x-client-id"] == "client-test"
            assert request.headers["x-api-key"] == "api-test"
            assert request.headers["x-idempotency-key"] == "request-once"
            assert request.headers["x-signature"] == payout_signature(
                body, "checksum-test"
            )
            return httpx.Response(
                200,
                json={
                    "code": "00",
                    "data": {
                        "id": "payout-test-1",
                        "referenceId": "THV-WDR-1",
                        "approvalState": "PROCESSING",
                        "transactions": {
                            "0": {"state": "PROCESSING", "errorCode": None}
                        },
                    },
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gateway = PayOSPayoutGateway(
            client_id="client-test",
            api_key="api-test",
            checksum_key="checksum-test",
            client=client,
        )
        try:
            result = await gateway.create_payout(
                reference_id="THV-WDR-1",
                idempotency_key="request-once",
                amount_minor=200_000,
                description="Commission transfer",
                bank_bin="970415",
                account_number="0123456789",
            )
            assert result.provider_payout_id == "payout-test-1"
            assert result.state == "PROCESSING"
            assert len(requests) == 1
        finally:
            await gateway.close()

    asyncio.run(exercise())


def test_payout_gateway_keeps_provider_errors_ambiguous() -> None:
    async def exercise() -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"code": "500", "desc": "error"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gateway = PayOSPayoutGateway(
            client_id="client-test",
            api_key="api-test",
            checksum_key="checksum-test",
            client=client,
        )
        try:
            with pytest.raises(PayoutOutcomeUnknown):
                await gateway.create_payout(
                    reference_id="THV-WDR-2",
                    idempotency_key="request-two",
                    amount_minor=200_000,
                    description="Commission transfer",
                    bank_bin="970415",
                    account_number="0123456789",
                )
        finally:
            await gateway.close()

    asyncio.run(exercise())
