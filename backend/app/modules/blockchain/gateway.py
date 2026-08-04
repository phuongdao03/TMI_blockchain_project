import json
from dataclasses import dataclass
from pathlib import Path

from hexbytes import HexBytes
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt


class BlockchainGatewayError(Exception):
    """RPC, ABI, network, or contract validation failure."""


@dataclass(frozen=True, slots=True)
class CertificateRecord:
    dossier_hash: bytes
    metadata_hash: bytes
    revocation_reason_hash: bytes
    issued_at: int
    expires_at: int
    version: int
    revoked: bool


@dataclass(frozen=True, slots=True)
class TransactionReceipt:
    transaction_hash: str
    block_number: int
    succeeded: bool


class BlockchainGateway:
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
            abi_payload = json.loads(abi_path.read_text(encoding="utf-8"))
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

    def encode_issue_certificate(
        self,
        *,
        certificate_id: bytes,
        dossier_hash: bytes,
        metadata_hash: bytes,
        issued_at: int,
        expires_at: int,
    ) -> bytes:
        return self._encode(
            "issueCertificate",
            [
                self._bytes32(certificate_id),
                self._bytes32(dossier_hash),
                self._bytes32(metadata_hash),
                issued_at,
                expires_at,
            ],
        )

    def encode_update_certificate(
        self,
        *,
        certificate_id: bytes,
        dossier_hash: bytes,
        metadata_hash: bytes,
        version: int,
    ) -> bytes:
        return self._encode(
            "updateCertificate",
            [
                self._bytes32(certificate_id),
                self._bytes32(dossier_hash),
                self._bytes32(metadata_hash),
                version,
            ],
        )

    def encode_revoke_certificate(
        self,
        *,
        certificate_id: bytes,
        reason_hash: bytes,
    ) -> bytes:
        return self._encode(
            "revokeCertificate",
            [
                self._bytes32(certificate_id),
                self._bytes32(reason_hash),
            ],
        )

    async def get_certificate(self, certificate_id: bytes) -> CertificateRecord:
        await self.validate_chain()
        try:
            result = await self._contract.functions.getCertificate(
                self._bytes32(certificate_id)
            ).call()
        except Exception as exc:
            raise BlockchainGatewayError("Contract read failed.") from exc
        return CertificateRecord(
            dossier_hash=bytes(result[0]),
            metadata_hash=bytes(result[1]),
            revocation_reason_hash=bytes(result[2]),
            issued_at=int(result[3]),
            expires_at=int(result[4]),
            version=int(result[5]),
            revoked=bool(result[6]),
        )

    async def pending_nonce(self, signer: str) -> int:
        await self.validate_chain()
        try:
            return await self._web3.eth.get_transaction_count(
                Web3.to_checksum_address(signer),
                "pending",
            )
        except Exception as exc:
            raise BlockchainGatewayError("Could not resolve signer nonce.") from exc

    async def estimate_gas(self, *, signer: str, payload: bytes) -> int:
        await self.validate_chain()
        try:
            return await self._web3.eth.estimate_gas(
                {
                    "from": Web3.to_checksum_address(signer),
                    "to": self.contract_address,
                    "data": HexBytes(payload),
                }
            )
        except Exception as exc:
            raise BlockchainGatewayError("Transaction gas estimation failed.") from exc

    async def gas_price(self) -> int:
        await self.validate_chain()
        try:
            return await self._web3.eth.gas_price
        except Exception as exc:
            raise BlockchainGatewayError("Could not resolve gas price.") from exc

    async def broadcast(self, raw_transaction: bytes) -> str:
        await self.validate_chain()
        try:
            tx_hash = await self._web3.eth.send_raw_transaction(raw_transaction)
        except Exception as exc:
            raise BlockchainGatewayError("Transaction broadcast failed.") from exc
        return tx_hash.to_0x_hex()

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
        return TransactionReceipt(
            transaction_hash=HexBytes(receipt["transactionHash"]).to_0x_hex(),
            block_number=int(receipt["blockNumber"]),
            succeeded=int(receipt["status"]) == 1,
        )

    async def latest_block_number(self) -> int:
        await self.validate_chain()
        try:
            return await self._web3.eth.block_number
        except Exception as exc:
            raise BlockchainGatewayError("Latest block lookup failed.") from exc

    def _encode(self, function_name: str, arguments: list[object]) -> bytes:
        try:
            encoded = self._contract.encode_abi(
                function_name,
                args=arguments,
            )
        except Exception as exc:
            raise BlockchainGatewayError("Contract call encoding failed.") from exc
        return bytes.fromhex(encoded.removeprefix("0x"))

    @staticmethod
    def _bytes32(value: bytes) -> bytes:
        if len(value) != 32:
            raise BlockchainGatewayError("Contract hash must be 32 bytes.")
        return value

    async def close(self) -> None:
        provider = self._web3.provider
        disconnect = getattr(provider, "disconnect", None)
        if disconnect is not None:
            await disconnect()
