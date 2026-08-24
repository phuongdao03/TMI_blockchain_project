import json
from dataclasses import dataclass
from pathlib import Path

from hexbytes import HexBytes
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt

SUPPORTED_CHAINS = {"local": 31_337, "amoy": 80_002, "polygon": 137}


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
class DocumentEvidenceRecord:
    commitment: bytes
    previous_evidence_key: bytes
    recorded_at: int
    version: int


@dataclass(frozen=True, slots=True)
class TransactionReceipt:
    transaction_hash: str
    block_number: int
    block_hash: str
    contract_address: str
    event_names: tuple[str, ...]
    succeeded: bool


@dataclass(frozen=True, slots=True)
class ChainTransaction:
    transaction_hash: str
    sender: str
    recipient: str
    data: bytes
    chain_id: int
    value: int


_EVENT_TOPICS = {
    Web3.keccak(
        text="CertificateIssued(bytes32,bytes32,bytes32,uint64,uint64)"
    ).to_0x_hex(): "CertificateIssued",
    Web3.keccak(
        text="CertificateUpdated(bytes32,bytes32,bytes32,uint32)"
    ).to_0x_hex(): "CertificateUpdated",
    Web3.keccak(text="CertificateRevoked(bytes32,bytes32)").to_0x_hex(): (
        "CertificateRevoked"
    ),
    Web3.keccak(
        text="DocumentEvidenceAnchored(bytes32,bytes32,bytes32,uint32,uint64)"
    ).to_0x_hex(): "DocumentEvidenceAnchored",
}


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

    def encode_anchor_document_evidence(
        self,
        *,
        evidence_key: bytes,
        commitment: bytes,
        previous_evidence_key: bytes,
        version: int,
        recorded_at: int,
    ) -> bytes:
        return self._encode(
            "anchorDocumentEvidence",
            [
                self._bytes32(evidence_key),
                self._bytes32(commitment),
                self._bytes32(previous_evidence_key),
                version,
                recorded_at,
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
        return self._certificate_record(result)

    async def get_certificate_version(
        self,
        certificate_id: bytes,
        version: int,
    ) -> CertificateRecord:
        """Read the immutable chain snapshot for a certificate version."""
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or not 1 <= version <= 2**32 - 1
        ):
            raise BlockchainGatewayError("Certificate version is invalid.")
        await self.validate_chain()
        try:
            result = await self._contract.functions.getCertificateVersion(
                self._bytes32(certificate_id),
                version,
            ).call()
        except Exception as exc:
            raise BlockchainGatewayError(
                "Contract historical version read failed."
            ) from exc
        return self._certificate_record(result)

    @staticmethod
    def _certificate_record(result: object) -> CertificateRecord:
        try:
            if not isinstance(result, (list, tuple)):
                raise TypeError("Contract certificate response must be a sequence.")
            values: tuple[object, ...] = tuple(result)
            (
                dossier_hash,
                metadata_hash,
                revocation_reason_hash,
                issued_at,
                expires_at,
                version,
                revoked,
            ) = values
            if (
                not isinstance(
                    dossier_hash,
                    (bytes, bytearray),
                )
                or not isinstance(
                    metadata_hash,
                    (bytes, bytearray),
                )
                or not isinstance(
                    revocation_reason_hash,
                    (bytes, bytearray),
                )
                or isinstance(issued_at, bool)
                or not isinstance(issued_at, int)
                or isinstance(expires_at, bool)
                or not isinstance(expires_at, int)
                or isinstance(version, bool)
                or not isinstance(version, int)
                or not isinstance(revoked, bool)
            ):
                raise TypeError("Contract certificate response has invalid values.")
            return CertificateRecord(
                dossier_hash=bytes(dossier_hash),
                metadata_hash=bytes(metadata_hash),
                revocation_reason_hash=bytes(revocation_reason_hash),
                issued_at=issued_at,
                expires_at=expires_at,
                version=version,
                revoked=revoked,
            )
        except (IndexError, TypeError, ValueError) as exc:
            raise BlockchainGatewayError(
                "Contract certificate response is invalid."
            ) from exc

    async def get_document_evidence(
        self,
        evidence_key: bytes,
    ) -> DocumentEvidenceRecord:
        await self.validate_chain()
        try:
            result = await self._contract.functions.getDocumentEvidence(
                self._bytes32(evidence_key)
            ).call()
        except Exception as exc:
            raise BlockchainGatewayError("Document evidence read failed.") from exc
        return DocumentEvidenceRecord(
            commitment=bytes(result[0]),
            previous_evidence_key=bytes(result[1]),
            recorded_at=int(result[2]),
            version=int(result[3]),
        )

    async def verify_document_evidence(
        self,
        *,
        evidence_key: bytes,
        commitment: bytes,
    ) -> bool:
        await self.validate_chain()
        try:
            return bool(
                await self._contract.functions.verifyDocumentEvidence(
                    self._bytes32(evidence_key),
                    self._bytes32(commitment),
                ).call()
            )
        except Exception as exc:
            raise BlockchainGatewayError(
                "Document evidence verification failed."
            ) from exc

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

    async def has_issuer_role(self, wallet_address: str) -> bool:
        """Check the existing contract role used for write operations."""
        await self.validate_chain()
        try:
            return bool(
                await self._contract.functions.hasRole(
                    Web3.keccak(text="ISSUER_ROLE"),
                    Web3.to_checksum_address(wallet_address),
                ).call()
            )
        except Exception as exc:
            raise BlockchainGatewayError("Signer role lookup failed.") from exc

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
            block_hash=HexBytes(receipt["blockHash"]).to_0x_hex(),
            contract_address=str(receipt["to"] or ""),
            event_names=tuple(
                event_name
                for log in receipt["logs"]
                if str(log["address"]).lower() == self.contract_address.lower()
                and log["topics"]
                for event_name in [
                    _EVENT_TOPICS.get(HexBytes(log["topics"][0]).to_0x_hex())
                ]
                if event_name is not None
            ),
            succeeded=int(receipt["status"]) == 1,
        )

    async def latest_block_number(self) -> int:
        await self.validate_chain()
        try:
            return await self._web3.eth.block_number
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
