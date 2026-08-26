"""Read and calldata gateway for the append-only ``THVProofRegistry``.

The registry deliberately remains separate from the legacy CertificateRegistry
gateway.  It does not sign or broadcast transactions; the human-controlled
wallet performs that final action in the client.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from hexbytes import HexBytes
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt

from app.modules.blockchain.gateway import (
    BlockchainGatewayError,
    ChainTransaction,
    TransactionReceipt,
)

_PROOF_RECORDED_TOPIC = Web3.keccak(
    text="ProofRecorded(bytes32,bytes32,uint64,address,uint64)"
).hex()


@dataclass(frozen=True, slots=True)
class THVProofRecord:
    asset_id: bytes
    proof_hash: bytes
    version: int
    recorded_at: int
    signer: str
    exists: bool


class THVProofRegistryGateway:
    """Constrained transport for one known THVProofRegistry deployment."""

    def __init__(
        self,
        *,
        rpc_url: str,
        network: str,
        chain_id: int,
        contract_address: str,
        abi_path: Path,
        allowed_networks: dict[str, int],
        allowed_contracts: dict[str, set[str]],
    ) -> None:
        expected_chain = allowed_networks.get(network)
        if expected_chain != chain_id:
            raise BlockchainGatewayError("Blockchain network is not allowed.")
        normalized_contracts = {
            value.lower() for value in allowed_contracts.get(network, set())
        }
        if contract_address.lower() not in normalized_contracts:
            raise BlockchainGatewayError("Contract address is not allowed.")
        if not Web3.is_address(contract_address):
            raise BlockchainGatewayError("Contract address is invalid.")
        try:
            # Tooling may emit a UTF-8 BOM for checked-in ABI artifacts. Treat
            # it as an encoding marker, never as ABI data.
            abi_payload = json.loads(abi_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise BlockchainGatewayError("Contract ABI is unavailable.") from exc
        if not isinstance(abi_payload, list):
            raise BlockchainGatewayError("Contract ABI is invalid.")

        self.network = network
        self.chain_id = chain_id
        self.contract_address = Web3.to_checksum_address(contract_address)
        self._web3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self._contract = self._web3.eth.contract(
            address=self.contract_address,
            abi=abi_payload,
        )

    async def validate_chain(self) -> None:
        try:
            actual_chain = await self._web3.eth.chain_id
        except Exception as exc:
            raise BlockchainGatewayError("Blockchain RPC is unavailable.") from exc
        if actual_chain != self.chain_id:
            raise BlockchainGatewayError("Blockchain chain ID does not match.")

    def encode_record_proof(
        self,
        *,
        asset_id: bytes,
        proof_hash: bytes,
        version: int,
    ) -> bytes:
        return self._encode(
            "recordProof",
            [
                self._bytes32(asset_id, nonzero=True),
                self._bytes32(proof_hash, nonzero=True),
                self._version(version),
            ],
        )

    async def get_proof(self, asset_id: bytes, version: int) -> THVProofRecord:
        await self.validate_chain()
        try:
            result = await self._contract.functions.getProof(
                self._bytes32(asset_id, nonzero=True),
                self._version(version),
            ).call()
        except Exception as exc:
            raise BlockchainGatewayError("THV proof registry read failed.") from exc
        return self._proof_record(result)

    async def verify_proof(
        self,
        *,
        asset_id: bytes,
        version: int,
        expected_hash: bytes,
    ) -> bool:
        await self.validate_chain()
        try:
            return bool(
                await self._contract.functions.verifyProof(
                    self._bytes32(asset_id, nonzero=True),
                    self._version(version),
                    self._bytes32(expected_hash),
                ).call()
            )
        except Exception as exc:
            raise BlockchainGatewayError("THV proof verification failed.") from exc

    async def has_verifier_role(self, wallet_address: str) -> bool:
        await self.validate_chain()
        try:
            return bool(
                await self._contract.functions.hasRole(
                    Web3.keccak(text="VERIFIER_ROLE"),
                    Web3.to_checksum_address(wallet_address),
                ).call()
            )
        except Exception as exc:
            raise BlockchainGatewayError("Signer role lookup failed.") from exc

    async def estimate_gas(self, *, signer: str, payload: bytes) -> int:
        await self.validate_chain()
        try:
            return int(
                await self._web3.eth.estimate_gas(
                    {
                        "from": Web3.to_checksum_address(signer),
                        "to": self.contract_address,
                        "data": HexBytes(payload),
                    }
                )
            )
        except Exception as exc:
            raise BlockchainGatewayError("Transaction gas estimation failed.") from exc

    async def gas_price(self) -> int:
        await self.validate_chain()
        try:
            return int(await self._web3.eth.gas_price)
        except Exception as exc:
            raise BlockchainGatewayError("Could not resolve gas price.") from exc

    async def balance(self, wallet_address: str) -> int:
        await self.validate_chain()
        try:
            return int(
                await self._web3.eth.get_balance(
                    Web3.to_checksum_address(wallet_address)
                )
            )
        except Exception as exc:
            raise BlockchainGatewayError("Could not resolve wallet balance.") from exc

    async def transaction(self, tx_hash: str) -> ChainTransaction | None:
        await self.validate_chain()
        try:
            transaction = await self._web3.eth.get_transaction(HexBytes(tx_hash))
        except TransactionNotFound:
            return None
        except Exception as exc:
            raise BlockchainGatewayError("Transaction lookup failed.") from exc
        sender = transaction.get("from")
        recipient = transaction.get("to")
        if sender is None or recipient is None:
            raise BlockchainGatewayError("Transaction sender or recipient is missing.")
        payload = transaction.get("input", transaction.get("data", b""))
        supplied_chain_id = transaction.get("chainId")
        return ChainTransaction(
            transaction_hash=HexBytes(transaction["hash"]).to_0x_hex(),
            sender=Web3.to_checksum_address(str(sender)),
            recipient=Web3.to_checksum_address(str(recipient)),
            data=bytes(HexBytes(payload)),
            chain_id=(
                int(supplied_chain_id)
                if supplied_chain_id is not None
                else self.chain_id
            ),
            value=int(transaction.get("value", 0)),
        )

    async def receipt(self, tx_hash: str) -> TransactionReceipt | None:
        await self.validate_chain()
        try:
            receipt: TxReceipt = await self._web3.eth.get_transaction_receipt(
                HexBytes(tx_hash)
            )
        except TransactionNotFound:
            return None
        except Exception as exc:
            raise BlockchainGatewayError("Transaction receipt lookup failed.") from exc
        event_names = tuple(
            "ProofRecorded"
            for log in receipt["logs"]
            if str(log["address"]).lower() == self.contract_address.lower()
            and log["topics"]
            and HexBytes(log["topics"][0]).to_0x_hex().lower()
            == _PROOF_RECORDED_TOPIC.lower()
        )
        return TransactionReceipt(
            transaction_hash=HexBytes(receipt["transactionHash"]).to_0x_hex(),
            block_number=int(receipt["blockNumber"]),
            block_hash=HexBytes(receipt["blockHash"]).to_0x_hex(),
            contract_address=str(receipt["to"] or ""),
            event_names=event_names,
            succeeded=int(receipt["status"]) == 1,
        )

    async def latest_block_number(self) -> int:
        await self.validate_chain()
        try:
            return int(await self._web3.eth.block_number)
        except Exception as exc:
            raise BlockchainGatewayError("Latest block lookup failed.") from exc

    async def block_hash(self, block_number: int) -> str:
        await self.validate_chain()
        try:
            block = await self._web3.eth.get_block(block_number)
            return HexBytes(block["hash"]).to_0x_hex()
        except Exception as exc:
            raise BlockchainGatewayError("Canonical block lookup failed.") from exc

    def _encode(self, function_name: str, arguments: list[object]) -> bytes:
        try:
            encoded = self._contract.encode_abi(function_name, args=arguments)
        except Exception as exc:
            raise BlockchainGatewayError("Contract call encoding failed.") from exc
        return bytes.fromhex(encoded.removeprefix("0x"))

    @staticmethod
    def _proof_record(result: object) -> THVProofRecord:
        try:
            if not isinstance(result, (tuple, list)):
                raise TypeError("THV proof response is not a tuple.")
            values: tuple[object, ...] = tuple(result)
            if len(values) == 1 and isinstance(values[0], (tuple, list)):
                values = tuple(values[0])
            return THVProofRecord(
                asset_id=bytes(cast(bytes, values[0])),
                proof_hash=bytes(cast(bytes, values[1])),
                version=int(cast(int, values[2])),
                recorded_at=int(cast(int, values[3])),
                signer=Web3.to_checksum_address(str(values[4])),
                exists=bool(values[5]),
            )
        except (IndexError, TypeError, ValueError) as exc:
            raise BlockchainGatewayError(
                "THV proof registry response is invalid."
            ) from exc

    @staticmethod
    def _bytes32(value: bytes, *, nonzero: bool = False) -> bytes:
        if len(value) != 32:
            raise BlockchainGatewayError("Contract hash must be 32 bytes.")
        if nonzero and value == bytes(32):
            raise BlockchainGatewayError("Contract hash must not be zero.")
        return value

    @staticmethod
    def _version(value: int) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= 2**64 - 1
        ):
            raise BlockchainGatewayError("Proof version is invalid.")
        return value

    async def close(self) -> None:
        provider = self._web3.provider
        disconnect = getattr(provider, "disconnect", None)
        if disconnect is not None:
            await disconnect()
