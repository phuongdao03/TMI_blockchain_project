from typing import Protocol

from eth_account import Account
from eth_account.datastructures import SignedTransaction
from web3 import Web3


class TransactionSigner(Protocol):
    @property
    def address(self) -> str: ...

    def sign(self, transaction: dict[str, int | str]) -> bytes: ...


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

    def sign(self, transaction: dict[str, int | str]) -> bytes:
        payload = dict(transaction)
        if "to" in payload:
            payload["to"] = Web3.to_checksum_address(
                str(payload["to"])
            )
        signed: SignedTransaction = self._account.sign_transaction(payload)
        return bytes(signed.raw_transaction)
