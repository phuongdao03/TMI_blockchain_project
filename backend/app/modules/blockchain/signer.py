from typing import Protocol

import httpx
from eth_account import Account
from eth_account.datastructures import SignedTransaction
from web3 import Web3


class TransactionSigner(Protocol):
    @property
    def address(self) -> str: ...

    async def sign(self, transaction: dict[str, int | str]) -> bytes: ...

    async def aclose(self) -> None: ...


class LocalPrivateKeySigner:
    def __init__(self, private_key: str) -> None:
        if not private_key:
            raise ValueError("Blockchain signer private key is not configured.")
        try:
            account = Account.from_key(private_key)
        except ValueError as exc:
            raise ValueError("Blockchain signer private key is invalid.") from exc
        self._account = account

    @property
    def address(self) -> str:
        return str(self._account.address)

    async def sign(self, transaction: dict[str, int | str]) -> bytes:
        payload = dict(transaction)
        if "to" in payload:
            payload["to"] = Web3.to_checksum_address(str(payload["to"]))
        signed: SignedTransaction = self._account.sign_transaction(payload)
        return bytes(signed.raw_transaction)

    async def aclose(self) -> None:
        return None


class ManagedKeySigner:
    def __init__(
        self,
        *,
        endpoint: str,
        key_id: str,
        expected_address: str,
        timeout_seconds: float = 8.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("Managed signer endpoint must use HTTPS.")
        if not key_id.strip():
            raise ValueError("Managed signer key ID is required.")
        if not Web3.is_address(expected_address):
            raise ValueError("Managed signer address is invalid.")
        self._endpoint = endpoint
        self._key_id = key_id
        self._address = Web3.to_checksum_address(expected_address)
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)

    @property
    def address(self) -> str:
        return self._address

    async def sign(self, transaction: dict[str, int | str]) -> bytes:
        try:
            response = await self._client.post(
                self._endpoint,
                json={"keyId": self._key_id, "transaction": transaction},
            )
            response.raise_for_status()
            payload = response.json()
            signer_address = str(payload["signerAddress"])
            raw_hex = str(payload["rawTransaction"])
            raw_transaction = bytes.fromhex(raw_hex.removeprefix("0x"))
            recovered = Account.recover_transaction(raw_transaction)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Managed signer request failed.") from exc
        if (
            not Web3.is_address(signer_address)
            or Web3.to_checksum_address(signer_address) != self._address
            or Web3.to_checksum_address(recovered) != self._address
        ):
            raise RuntimeError("Managed signer returned an unexpected address.")
        return raw_transaction

    async def aclose(self) -> None:
        await self._client.aclose()


def create_transaction_signer(
    *,
    mode: str,
    private_key: str,
    managed_url: str,
    managed_key_id: str,
    managed_expected_address: str,
    managed_timeout_seconds: float,
) -> TransactionSigner:
    if mode == "managed":
        return ManagedKeySigner(
            endpoint=managed_url,
            key_id=managed_key_id,
            expected_address=managed_expected_address,
            timeout_seconds=managed_timeout_seconds,
        )
    if mode == "local":
        return LocalPrivateKeySigner(private_key)
    raise ValueError("Unsupported blockchain signer mode.")
