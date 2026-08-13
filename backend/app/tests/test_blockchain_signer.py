import asyncio

import httpx
import pytest
from eth_account import Account

from app.modules.blockchain.signer import LocalPrivateKeySigner, ManagedKeySigner

PRIVATE_KEY = "0x" + "11" * 32
OTHER_PRIVATE_KEY = "0x" + "22" * 32
TRANSACTION: dict[str, int | str] = {
    "chainId": 137,
    "nonce": 3,
    "gas": 100_000,
    "gasPrice": 30_000_000_000,
    "to": "0x" + "33" * 20,
    "data": "0x1234",
    "value": 0,
}


def test_local_signer_implements_async_signing_interface() -> None:
    async def exercise() -> None:
        signer = LocalPrivateKeySigner(PRIVATE_KEY)
        raw_transaction = await signer.sign(TRANSACTION)
        assert Account.recover_transaction(raw_transaction) == signer.address
        await signer.aclose()

    asyncio.run(exercise())


def test_managed_signer_verifies_returned_signature_and_identity() -> None:
    async def exercise() -> None:
        account = Account.from_key(PRIVATE_KEY)

        def handler(request: httpx.Request) -> httpx.Response:
            payload = request.read().decode()
            assert '"keyId":"projects/tmi/keys/certificate-issuer"' in payload
            signed = account.sign_transaction(TRANSACTION)
            return httpx.Response(
                200,
                json={
                    "signerAddress": account.address,
                    "rawTransaction": signed.raw_transaction.to_0x_hex(),
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        signer = ManagedKeySigner(
            endpoint="https://signer.internal.example/v1/sign",
            key_id="projects/tmi/keys/certificate-issuer",
            expected_address=account.address,
            client=client,
        )

        raw_transaction = await signer.sign(TRANSACTION)
        assert Account.recover_transaction(raw_transaction) == account.address
        await signer.aclose()

    asyncio.run(exercise())


def test_managed_signer_rejects_untrusted_endpoint_and_wrong_key() -> None:
    address = Account.from_key(PRIVATE_KEY).address
    with pytest.raises(ValueError, match="HTTPS"):
        ManagedKeySigner(
            endpoint="http://signer.internal/v1/sign",
            key_id="key",
            expected_address=address,
        )

    async def exercise() -> None:
        other = Account.from_key(OTHER_PRIVATE_KEY)
        raw = other.sign_transaction(TRANSACTION).raw_transaction.to_0x_hex()
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={"signerAddress": other.address, "rawTransaction": raw},
                )
            )
        )
        signer = ManagedKeySigner(
            endpoint="https://signer.internal.example/v1/sign",
            key_id="key",
            expected_address=address,
            client=client,
        )
        with pytest.raises(RuntimeError, match="unexpected address"):
            await signer.sign(TRANSACTION)
        await signer.aclose()

    asyncio.run(exercise())
