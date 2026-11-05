"""Narrow payOS payout adapter; calls happen only from the gated worker."""

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


class PayoutGatewayError(RuntimeError):
    """A provider response could not be safely interpreted."""


class PayoutOutcomeUnknown(PayoutGatewayError):
    """The provider may have accepted the payout; funds must remain reserved."""


@dataclass(frozen=True)
class PayoutResult:
    provider_payout_id: str
    reference_id: str
    state: str
    error_code: str | None = None


def _encoded(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        value = str(value).lower()
    elif isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return quote(str(value), safe="-_.!~*'()")


def payout_signature(data: Mapping[str, object], checksum_key: str) -> str:
    """Build payOS's payout signature, distinct from payment-request signing."""
    canonical = "&".join(
        f"{_encoded(key)}={_encoded(data[key])}" for key in sorted(data)
    )
    return hmac.new(
        checksum_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _data(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise PayoutOutcomeUnknown("payOS returned invalid payout JSON.") from exc
    if not isinstance(payload, dict) or payload.get("code") != "00":
        raise PayoutOutcomeUnknown("payOS returned an unconfirmed payout result.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise PayoutOutcomeUnknown("payOS payout response omitted result data.")
    return data


def _result(data: dict[str, Any], fallback_reference: str) -> PayoutResult:
    transactions = data.get("transactions")
    transaction: dict[str, Any] = {}
    if isinstance(transactions, list) and transactions:
        transaction = transactions[0] if isinstance(transactions[0], dict) else {}
    elif isinstance(transactions, dict):
        transaction = next(
            (value for value in transactions.values() if isinstance(value, dict)), {}
        )
    payout_id = data.get("id")
    reference_id = data.get("referenceId", fallback_reference)
    state = transaction.get("state") or data.get("approvalState")
    if (
        not isinstance(payout_id, str)
        or not 1 <= len(payout_id) <= 128
        or re.fullmatch(r"[A-Za-z0-9_-]+", payout_id) is None
    ):
        raise PayoutOutcomeUnknown("payOS payout response omitted provider id.")
    if not isinstance(reference_id, str) or reference_id != fallback_reference:
        raise PayoutOutcomeUnknown("payOS payout reference did not match.")
    if not isinstance(state, str) or not state:
        raise PayoutOutcomeUnknown("payOS payout response omitted state.")
    error_code = transaction.get("errorCode")
    return PayoutResult(
        provider_payout_id=payout_id,
        reference_id=reference_id,
        state=state.upper(),
        error_code=str(error_code)[:64] if error_code is not None else None,
    )


class PayOSPayoutGateway:
    def __init__(
        self,
        *,
        client_id: str,
        api_key: str,
        checksum_key: str,
        base_url: str = "https://api-merchant.payos.vn",
        timeout_seconds: float = 8.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not all((client_id, api_key, checksum_key)):
            raise RuntimeError("payOS payout credentials are not configured.")
        if not base_url.startswith("https://"):
            raise RuntimeError("payOS payout API URL must use HTTPS.")
        self._checksum_key = checksum_key
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(
            headers={"x-client-id": client_id, "x-api-key": api_key},
            timeout=httpx.Timeout(timeout_seconds),
        )
        if client is not None:
            self._client.headers.update(
                {"x-client-id": client_id, "x-api-key": api_key}
            )

    async def create_payout(
        self,
        *,
        reference_id: str,
        idempotency_key: str,
        amount_minor: int,
        description: str,
        bank_bin: str,
        account_number: str,
    ) -> PayoutResult:
        if amount_minor <= 0 or not reference_id or not idempotency_key:
            raise ValueError("Payout identifiers and amount must be valid.")
        body: dict[str, object] = {
            "referenceId": reference_id,
            "amount": amount_minor,
            "description": description[:25],
            "toBin": bank_bin,
            "toAccountNumber": account_number,
        }
        try:
            response = await self._client.post(
                f"{self._base_url}/v1/payouts",
                json=body,
                headers={
                    "x-idempotency-key": idempotency_key,
                    "x-signature": payout_signature(body, self._checksum_key),
                },
            )
        except httpx.HTTPError as exc:
            raise PayoutOutcomeUnknown(
                "payOS payout request outcome is unknown."
            ) from exc
        if response.status_code >= 500 or response.status_code == 429:
            raise PayoutOutcomeUnknown("payOS payout request outcome is unknown.")
        if response.status_code >= 400:
            raise PayoutOutcomeUnknown("payOS did not confirm payout acceptance.")
        return _result(_data(response), reference_id)

    async def get_payout(
        self, payout_id: str, *, expected_reference_id: str
    ) -> PayoutResult:
        if (
            not 1 <= len(payout_id) <= 128
            or re.fullmatch(r"[A-Za-z0-9_-]+", payout_id) is None
        ):
            raise ValueError("Provider payout id is invalid.")
        try:
            response = await self._client.get(
                f"{self._base_url}/v1/payouts/{payout_id}"
            )
        except httpx.HTTPError as exc:
            raise PayoutOutcomeUnknown("payOS payout status is unavailable.") from exc
        if response.status_code >= 400:
            raise PayoutOutcomeUnknown("payOS payout status is unavailable.")
        data = _data(response)
        if data.get("id") != payout_id:
            raise PayoutOutcomeUnknown("payOS payout id did not match the request.")
        reference = data.get("referenceId")
        if reference != expected_reference_id:
            raise PayoutOutcomeUnknown("payOS payout reference did not match.")
        return _result(data, expected_reference_id)

    async def close(self) -> None:
        await self._client.aclose()
