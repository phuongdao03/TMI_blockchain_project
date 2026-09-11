"""Read and calldata gateway for the append-only ``THVProofRegistry``.

The registry deliberately remains separate from the legacy CertificateRegistry
gateway.  It does not sign or broadcast transactions; the human-controlled
wallet performs that final action in the client.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from hexbytes import HexBytes
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3
from web3.exceptions import TransactionNotFound
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import TxReceipt

from app.modules.blockchain.transport import (
    BlockchainGatewayError,
    ChainTransaction,
    ProofRecordedEvent,
    TransactionReceipt,
)

_PROOF_RECORDED_TOPIC = Web3.keccak(
    text="ProofRecorded(bytes32,bytes32,uint64,address,uint64)"
).to_0x_hex()
_MAX_LOG_BLOCK_SPAN = 10


@dataclass(frozen=True, slots=True)
class THVProofRecord:
    asset_id: bytes
    proof_hash: bytes
    version: int
    recorded_at: int
    signer: str
    exists: bool


@dataclass(frozen=True, slots=True)
class THVProofRecording:
    """Canonical transaction location for one exact ``ProofRecorded`` event."""

    transaction_hash: str
    block_number: int
    block_hash: str
    signer: str
    recorded_at: int


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
        if network in {"amoy", "polygon"}:
            self._web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
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
        proof_events = tuple(
            event
            for log in receipt["logs"]
            if (event := self._proof_recorded_event(log)) is not None
        )
        return TransactionReceipt(
            transaction_hash=HexBytes(receipt["transactionHash"]).to_0x_hex(),
            block_number=int(receipt["blockNumber"]),
            block_hash=HexBytes(receipt["blockHash"]).to_0x_hex(),
            contract_address=str(receipt["to"] or ""),
            event_names=tuple("ProofRecorded" for _event in proof_events),
            succeeded=int(receipt["status"]) == 1,
            proof_recorded_events=proof_events,
        )

    async def find_recording(
        self,
        *,
        asset_id: bytes,
        proof_hash: bytes,
        version: int,
        recorded_at: int,
    ) -> THVProofRecording | None:
        """Find an exact registry event when a browser lost the wallet callback.

        The contract stores the block timestamp in the proof. A timestamp-guided
        block search avoids scanning chain history and the indexed topics ensure
        that an unrelated transaction can never be attached to the dossier.
        """
        asset_id = self._bytes32(asset_id, nonzero=True)
        proof_hash = self._bytes32(proof_hash, nonzero=True)
        version = self._version(version)
        if recorded_at <= 0:
            raise BlockchainGatewayError("Proof recording timestamp is invalid.")
        await self.validate_chain()
        try:
            latest_block = int(await self._web3.eth.block_number)
            topics = [
                _PROOF_RECORDED_TOPIC,
                self._as_topic(asset_id),
                self._as_topic(proof_hash),
                self._as_topic(version.to_bytes(32, "big")),
            ]
            candidate = await self._first_block_at_or_after(
                recorded_at,
                latest_block=latest_block,
            )
            candidate_block = await self._web3.eth.get_block(candidate)
            if int(candidate_block["timestamp"]) != recorded_at:
                return None

            logs = []
            from_block = candidate
            while from_block <= latest_block:
                to_block = min(
                    latest_block,
                    from_block + _MAX_LOG_BLOCK_SPAN - 1,
                )
                logs.extend(
                    await self._web3.eth.get_logs(
                        {
                            "address": self.contract_address,
                            "fromBlock": from_block,
                            "toBlock": to_block,
                            "topics": topics,
                        }
                    )
                )
                if to_block >= latest_block:
                    break
                last_block = await self._web3.eth.get_block(to_block)
                if int(last_block["timestamp"]) > recorded_at:
                    break
                from_block = to_block + 1
        except BlockchainGatewayError:
            raise
        except Exception as exc:
            raise BlockchainGatewayError("ProofRecorded event lookup failed.") from exc

        matches: list[THVProofRecording] = []
        for log in logs:
            event = self._proof_recorded_event(log)
            if (
                event is None
                or event.asset_id != asset_id
                or event.proof_hash != proof_hash
                or event.version != version
                or event.timestamp != recorded_at
            ):
                continue
            try:
                matches.append(
                    THVProofRecording(
                        transaction_hash=HexBytes(log["transactionHash"]).to_0x_hex(),
                        block_number=int(log["blockNumber"]),
                        block_hash=HexBytes(log["blockHash"]).to_0x_hex(),
                        signer=event.signer,
                        recorded_at=event.timestamp,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise BlockchainGatewayError(
                    "ProofRecorded event location is invalid."
                ) from exc
        if len(matches) > 1:
            raise BlockchainGatewayError("ProofRecorded event is not unique.")
        return matches[0] if matches else None

    async def _first_block_at_or_after(
        self,
        timestamp: int,
        *,
        latest_block: int,
    ) -> int:
        low = 0
        high = latest_block
        while low < high:
            midpoint = (low + high) // 2
            block = await self._web3.eth.get_block(midpoint)
            if int(block["timestamp"]) < timestamp:
                low = midpoint + 1
            else:
                high = midpoint
        return low

    def _proof_recorded_event(self, log: object) -> ProofRecordedEvent | None:
        try:
            if not isinstance(log, Mapping):
                return None
            topics = log["topics"]
            if (
                str(log["address"]).lower() != self.contract_address.lower()
                or not isinstance(topics, (tuple, list))
                or len(topics) != 4
                or HexBytes(topics[0]).to_0x_hex().lower()
                != _PROOF_RECORDED_TOPIC.lower()
            ):
                return None
            data = bytes(HexBytes(log["data"]))
            if len(data) != 64:
                raise ValueError("ProofRecorded data length is invalid.")
            signer = Web3.to_checksum_address("0x" + data[12:32].hex())
            return ProofRecordedEvent(
                asset_id=bytes(HexBytes(topics[1])),
                proof_hash=bytes(HexBytes(topics[2])),
                version=int.from_bytes(bytes(HexBytes(topics[3])), "big"),
                signer=signer,
                timestamp=int.from_bytes(data[32:64], "big"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BlockchainGatewayError(
                "ProofRecorded event payload is invalid."
            ) from exc

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

    @staticmethod
    def _as_topic(value: bytes) -> str:
        return HexBytes(value).to_0x_hex()

    async def close(self) -> None:
        provider = self._web3.provider
        disconnect = getattr(provider, "disconnect", None)
        if disconnect is not None:
            await disconnect()
