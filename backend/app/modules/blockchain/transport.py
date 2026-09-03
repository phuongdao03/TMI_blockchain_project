"""Shared, contract-neutral blockchain transport types."""

from dataclasses import dataclass

SUPPORTED_CHAINS = {"local": 31_337, "amoy": 80_002, "polygon": 137}


class BlockchainGatewayError(Exception):
    """RPC, ABI, network, or contract validation failure."""


@dataclass(frozen=True, slots=True)
class ProofRecordedEvent:
    asset_id: bytes
    proof_hash: bytes
    version: int
    signer: str
    timestamp: int


@dataclass(frozen=True, slots=True)
class TransactionReceipt:
    transaction_hash: str
    block_number: int
    block_hash: str
    contract_address: str
    event_names: tuple[str, ...]
    succeeded: bool
    proof_recorded_events: tuple[ProofRecordedEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class ChainTransaction:
    transaction_hash: str
    sender: str
    recipient: str
    data: bytes
    chain_id: int
    value: int
