"""Application service for human-signed THV proof registry writes.

This is intentionally parallel to the legacy certificate blockchain flow.  It
only prepares a constrained MetaMask-compatible request after a dossier has a
server-side approval signal; it never receives a wallet private key or sends a
transaction itself.
"""

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import (
    BlockchainConflictError,
    BlockchainForbiddenError,
    BlockchainNotFoundError,
    BlockchainUnavailableError,
)
from app.modules.blockchain.gateway import BlockchainGatewayError
from app.modules.blockchain.human_signing import normalize_wallet_address
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionIntent,
    BlockchainTransactionIntentStatus,
    BlockchainTransactionStatus,
    BlockchainWalletLink,
    BlockchainWalletLinkStatus,
)
from app.modules.blockchain.proof_registry_gateway import (
    THVProofRecord,
    THVProofRegistryGateway,
)
from app.modules.dossiers.errors import DossierNotFoundError
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVersion

_ASSET_ID_DOMAIN = b"THVProofRegistry:asset:v1:"
_HEX_BYTES32 = re.compile(r"0x[0-9a-fA-F]{64}")
_CANONICAL_HASH = re.compile(r"[0-9a-fA-F]{64}")
_PROOF_CONFIRMED_EVENT = "blockchain.anchored"


@dataclass(frozen=True, slots=True)
class THVProofRegistryIntentView:
    intent_id: UUID
    transaction_id: UUID
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version: int
    asset_id: str
    proof_hash: str
    network: str
    chain_id: int
    contract_address: str
    transaction_request: dict[str, str]
    estimated_gas: int
    gas_price_wei: int
    wallet_balance_wei: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class THVProofRegistryStatusView:
    transaction_id: UUID
    status: BlockchainTransactionStatus
    tx_hash: str | None
    confirmations: int
    error_code: str | None
    error_message: str | None
    confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class THVProofRegistryQueueItemView:
    transaction_id: UUID | None
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version: int
    proof_hash: str
    status: BlockchainTransactionStatus
    tx_hash: str | None
    confirmations: int
    error_code: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class THVProofRegistryProofView:
    asset_id: str
    proof_hash: str
    version: int
    recorded_at: int
    signer: str
    exists: bool


@dataclass(frozen=True, slots=True)
class THVProofRegistryVerificationView:
    asset_id: str
    version: int
    expected_hash: str
    verified: bool


@dataclass(frozen=True, slots=True)
class _ApprovedVersionContext:
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    version: int
    canonical_hash: str
    version_id: UUID


def derive_thv_asset_id(dossier_id: UUID) -> bytes:
    """Create a stable opaque asset ID without placing dossier data on-chain."""
    return hashlib.sha256(_ASSET_ID_DOMAIN + dossier_id.bytes).digest()


class THVProofRegistryService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: THVProofRegistryGateway,
        network: str,
        chain_id: int,
        contract_address: str,
        signing_enabled: bool,
        payload_cipher: OutboxPayloadCipher,
        required_confirmations: int = 1,
        intent_ttl: timedelta = timedelta(minutes=10),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if gateway.contract_address.lower() != contract_address.lower():
            raise ValueError("THV proof registry contract address is inconsistent.")
        self._session = session
        self._gateway = gateway
        self._network = network
        self._chain_id = chain_id
        self._contract_address = contract_address.lower()
        self._signing_enabled = signing_enabled
        self._payload_cipher = payload_cipher
        self._outbox = OutboxRepository(session)
        self._required_confirmations = required_confirmations
        self._intent_ttl = intent_ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    async def signing_queue(
        self, principal: AuthPrincipal
    ) -> list[THVProofRegistryQueueItemView]:
        """List current approved dossier versions not yet confirmed on registry."""
        self._require_signer(principal)
        self._require_enabled()
        async with self._session.begin():
            rows = (
                await self._session.execute(
                    select(Dossier, DossierVersion, BlockchainTransaction)
                    .join(
                        DossierVersion,
                        and_(
                            DossierVersion.dossier_id == Dossier.id,
                            DossierVersion.version_no == Dossier.current_version_no,
                        ),
                    )
                    .outerjoin(
                        BlockchainTransaction,
                        and_(
                            BlockchainTransaction.dossier_version_id
                            == DossierVersion.id,
                            BlockchainTransaction.network == self._network,
                            BlockchainTransaction.contract_address
                            == self._contract_address,
                            BlockchainTransaction.method == "recordProof",
                            BlockchainTransaction.payload_hash
                            == DossierVersion.canonical_hash,
                        ),
                    )
                    .where(
                        Dossier.status == DossierStatus.APPROVED,
                        Dossier.deleted_at.is_(None),
                        or_(
                            BlockchainTransaction.id.is_(None),
                            BlockchainTransaction.status
                            != BlockchainTransactionStatus.CONFIRMED,
                        ),
                    )
                    .order_by(Dossier.approved_at.asc(), Dossier.created_at.asc())
                    .limit(200)
                )
            ).all()
        return [
            THVProofRegistryQueueItemView(
                transaction_id=transaction.id if transaction else None,
                dossier_id=dossier.id,
                dossier_code=dossier.code,
                dossier_title=dossier.title,
                version=version.version_no,
                proof_hash=self._as_hex(bytes.fromhex(version.canonical_hash)),
                status=(
                    transaction.status
                    if transaction
                    else BlockchainTransactionStatus.CREATED
                ),
                tx_hash=transaction.tx_hash if transaction else None,
                confirmations=transaction.confirmations if transaction else 0,
                error_code=transaction.error_code if transaction else None,
                created_at=dossier.approved_at or version.submitted_at,
            )
            for dossier, version, transaction in rows
        ]

    async def prepare_record_proof_intent(
        self,
        principal: AuthPrincipal,
        *,
        dossier_id: UUID,
        version_no: int,
        connected_wallet: str,
    ) -> THVProofRegistryIntentView:
        """Prepare only an approved, role-authorized ``recordProof`` call."""
        self._require_signer(principal)
        self._require_enabled()
        wallet = await self._require_active_wallet(principal, connected_wallet)
        await self._require_verifier_role(wallet.wallet_address)
        context = await self._approved_version_context(dossier_id, version_no)
        asset_id = derive_thv_asset_id(context.dossier_id)
        proof_hash = bytes.fromhex(context.canonical_hash)
        existing = await self._read_proof(asset_id, context.version)
        if existing.exists:
            raise BlockchainConflictError(
                "This approved dossier version already has an immutable proof."
            )

        try:
            payload = self._gateway.encode_record_proof(
                asset_id=asset_id,
                proof_hash=proof_hash,
                version=context.version,
            )
            estimated_gas = await self._gateway.estimate_gas(
                signer=wallet.wallet_address,
                payload=payload,
            )
            gas_price = await self._gateway.gas_price()
            balance = await self._gateway.balance(wallet.wallet_address)
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof registry is unavailable for signing."
            ) from exc

        now = self._clock()
        async with self._session.begin():
            transaction = cast(
                BlockchainTransaction | None,
                await self._session.scalar(
                    select(BlockchainTransaction).where(
                        BlockchainTransaction.dossier_version_id == context.version_id,
                        BlockchainTransaction.network == self._network,
                        BlockchainTransaction.contract_address
                        == self._contract_address,
                        BlockchainTransaction.method == "recordProof",
                        BlockchainTransaction.payload_hash == context.canonical_hash,
                    )
                ),
            )
            if transaction is None:
                transaction = BlockchainTransaction(
                    id=uuid4(),
                    dossier_id=context.dossier_id,
                    dossier_version_id=context.version_id,
                    network=self._network,
                    chain_id=self._chain_id,
                    contract_address=self._contract_address,
                    method="recordProof",
                    payload_hash=context.canonical_hash,
                    status=BlockchainTransactionStatus.CREATED,
                )
                self._session.add(transaction)
                await self._session.flush()
            if transaction.status in {
                BlockchainTransactionStatus.BROADCAST,
                BlockchainTransactionStatus.CONFIRMED,
            }:
                raise BlockchainConflictError(
                    "This dossier version already has a submitted proof transaction."
                )
            current = cast(
                BlockchainTransactionIntent | None,
                await self._session.scalar(
                    select(BlockchainTransactionIntent).where(
                        BlockchainTransactionIntent.transaction_id == transaction.id,
                        BlockchainTransactionIntent.status
                        == BlockchainTransactionIntentStatus.PREPARED,
                    )
                ),
            )
            if current is not None and self._as_utc(current.expires_at) <= now:
                current.status = BlockchainTransactionIntentStatus.EXPIRED
                current = None
            if current is None:
                current = BlockchainTransactionIntent(
                    id=uuid4(),
                    transaction_id=transaction.id,
                    dossier_id=context.dossier_id,
                    dossier_version_id=context.version_id,
                    signer_user_id=principal.user_id,
                    expected_wallet_address=wallet.wallet_address,
                    network=self._network,
                    chain_id=self._chain_id,
                    contract_address=self._contract_address,
                    proof_hash=context.canonical_hash,
                    encoded_call_hash=hashlib.sha256(payload).hexdigest(),
                    status=BlockchainTransactionIntentStatus.PREPARED,
                    expires_at=now + self._intent_ttl,
                )
                self._session.add(current)
            elif (
                current.signer_user_id != principal.user_id
                or current.expected_wallet_address != wallet.wallet_address
            ):
                raise BlockchainConflictError("A signing request is already active.")
            transaction.status = BlockchainTransactionStatus.SIGNING
            await self._session.flush()

        return THVProofRegistryIntentView(
            intent_id=current.id,
            transaction_id=transaction.id,
            dossier_id=context.dossier_id,
            dossier_code=context.dossier_code,
            dossier_title=context.dossier_title,
            version=context.version,
            asset_id=self._as_hex(asset_id),
            proof_hash=self._as_hex(proof_hash),
            network=self._network,
            chain_id=self._chain_id,
            contract_address=self._contract_address,
            transaction_request={
                "to": self._contract_address,
                "data": self._as_hex(payload),
                "chainId": str(self._chain_id),
                "value": "0",
            },
            estimated_gas=estimated_gas,
            gas_price_wei=gas_price,
            wallet_balance_wei=balance,
            expires_at=current.expires_at,
        )

    async def submit_transaction(
        self,
        principal: AuthPrincipal,
        *,
        transaction_id: UUID,
        intent_id: UUID,
        transaction_hash: str,
        connected_wallet: str,
    ) -> THVProofRegistryStatusView:
        self._require_signer(principal)
        self._require_enabled()
        wallet = await self._require_active_wallet(principal, connected_wallet)
        async with self._session.begin():
            intent = await self._required_intent(intent_id)
            if intent.transaction_id != transaction_id:
                raise BlockchainConflictError("Transaction intent does not match.")
            expected_call_hash = intent.encoded_call_hash
            expected_wallet = intent.expected_wallet_address
            expected_contract = intent.contract_address
            expected_chain = int(intent.chain_id)
        try:
            chain_transaction = await self._gateway.transaction(transaction_hash)
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof transaction lookup is unavailable."
            ) from exc
        if chain_transaction is None:
            raise BlockchainConflictError("Blockchain transaction was not found.")
        if (
            chain_transaction.sender != expected_wallet
            or chain_transaction.sender != wallet.wallet_address
            or chain_transaction.recipient.lower() != expected_contract.lower()
            or chain_transaction.chain_id != expected_chain
            or chain_transaction.value != 0
            or hashlib.sha256(chain_transaction.data).hexdigest() != expected_call_hash
        ):
            raise BlockchainConflictError(
                "Blockchain transaction does not match intent."
            )
        now = self._clock()
        async with self._session.begin():
            intent = await self._required_intent(intent_id, for_update=True)
            transaction = await self._required_transaction(
                transaction_id, for_update=True
            )
            if (
                intent.signer_user_id != principal.user_id
                or intent.expected_wallet_address != wallet.wallet_address
                or intent.status is not BlockchainTransactionIntentStatus.PREPARED
                or self._as_utc(intent.expires_at) <= now
                or transaction.method != "recordProof"
                or transaction.contract_address.lower() != self._contract_address
            ):
                raise BlockchainConflictError(
                    "Blockchain signing intent is no longer valid."
                )
            if transaction.status not in {
                BlockchainTransactionStatus.CREATED,
                BlockchainTransactionStatus.SIGNING,
            }:
                raise BlockchainConflictError("Transaction cannot be submitted now.")
            transaction.status = BlockchainTransactionStatus.BROADCAST
            transaction.tx_hash = chain_transaction.transaction_hash
            transaction.signer_user_id = principal.user_id
            transaction.signer_wallet_address = wallet.wallet_address
            transaction.broadcast_at = now
            transaction.error_code = None
            transaction.error_message = None
            intent.status = BlockchainTransactionIntentStatus.SUBMITTED
            intent.submitted_at = now
            return self._status_view(transaction)

    async def transaction_status(
        self,
        principal: AuthPrincipal,
        *,
        transaction_id: UUID,
        reconcile: bool = True,
    ) -> THVProofRegistryStatusView:
        self._require_signer(principal)
        if reconcile:
            await self._reconcile(transaction_id)
        async with self._session.begin():
            return self._status_view(await self._required_transaction(transaction_id))

    async def _reconcile(self, transaction_id: UUID) -> None:
        async with self._session.begin():
            transaction = await self._required_transaction(transaction_id)
            if (
                transaction.status
                not in {
                    BlockchainTransactionStatus.BROADCAST,
                    BlockchainTransactionStatus.CONFIRMED,
                }
                or transaction.tx_hash is None
            ):
                return
            tx_hash = transaction.tx_hash
            dossier_id = transaction.dossier_id
            version_id = transaction.dossier_version_id
            proof_hash = transaction.payload_hash
            expected_signer = transaction.signer_wallet_address
        try:
            receipt = await self._gateway.receipt(tx_hash)
            if receipt is None:
                return
            if not receipt.succeeded:
                await self._fail_transaction(
                    transaction_id, "TRANSACTION_REVERTED", "Transaction reverted."
                )
                return
            if (
                receipt.transaction_hash.lower() != tx_hash.lower()
                or receipt.contract_address.lower() != self._contract_address
                or "ProofRecorded" not in receipt.event_names
            ):
                await self._fail_transaction(
                    transaction_id,
                    "RECEIPT_MISMATCH",
                    "Receipt contract, hash or ProofRecorded event does not match.",
                )
                return
            canonical_hash = await self._gateway.block_hash(receipt.block_number)
            if canonical_hash.lower() != receipt.block_hash.lower():
                await self._fail_transaction(
                    transaction_id, "CHAIN_REORG", "Receipt block is not canonical."
                )
                return
            latest_block = await self._gateway.latest_block_number()
            confirmations = max(0, latest_block - receipt.block_number + 1)
            async with self._session.begin():
                version = await self._session.get(DossierVersion, version_id)
            if version is None or version.dossier_id != dossier_id:
                await self._fail_transaction(
                    transaction_id, "CONTEXT_MISSING", "Proof context is unavailable."
                )
                return
            asset_id = derive_thv_asset_id(dossier_id)
            proof = await self._gateway.get_proof(asset_id, version.version_no)
            if (
                not proof.exists
                or proof.asset_id != asset_id
                or proof.proof_hash != bytes.fromhex(proof_hash)
                or proof.version != version.version_no
                or expected_signer is None
                or proof.signer.lower() != expected_signer.lower()
            ):
                await self._fail_transaction(
                    transaction_id,
                    "CHAIN_STATE_MISMATCH",
                    "On-chain proof does not match the frozen dossier proof.",
                )
                return
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof confirmation lookup is unavailable."
            ) from exc

        async with self._session.begin():
            transaction = await self._required_transaction(
                transaction_id, for_update=True
            )
            transaction.confirmations = confirmations
            transaction.receipt_block_number = receipt.block_number
            transaction.receipt_block_hash = receipt.block_hash
            transaction.receipt_event_name = "ProofRecorded"
            transaction.error_code = None
            transaction.error_message = None
            if (
                confirmations >= self._required_confirmations
                and transaction.status is not BlockchainTransactionStatus.CONFIRMED
            ):
                transaction.status = BlockchainTransactionStatus.CONFIRMED
                transaction.confirmed_at = transaction.confirmed_at or self._clock()
                dossier = await self._session.get(Dossier, transaction.dossier_id)
                if dossier is None:
                    raise BlockchainNotFoundError()
                self._add_confirmed_event(transaction, dossier.owner_user_id)

    def _add_confirmed_event(
        self, transaction: BlockchainTransaction, owner_user_id: UUID
    ) -> None:
        encrypted = self._payload_cipher.encrypt(
            {
                "dossier_id": str(transaction.dossier_id),
                "transaction_id": str(transaction.id),
                "transaction_hash": transaction.tx_hash or "",
                "owner_user_id": str(owner_user_id),
            },
            event_type=_PROOF_CONFIRMED_EVENT,
            aggregate_id=transaction.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=_PROOF_CONFIRMED_EVENT,
                aggregate_type="blockchain_transaction",
                aggregate_id=transaction.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=self._clock(),
            )
        )

    async def _fail_transaction(
        self, transaction_id: UUID, code: str, message: str
    ) -> None:
        async with self._session.begin():
            transaction = await self._required_transaction(
                transaction_id, for_update=True
            )
            if transaction.status is BlockchainTransactionStatus.CONFIRMED:
                return
            transaction.status = BlockchainTransactionStatus.FAILED
            transaction.error_code = code
            transaction.error_message = message

    async def get_proof(
        self,
        *,
        asset_id: str,
        version: int,
    ) -> THVProofRegistryProofView:
        normalized_asset_id = self._require_hex_bytes32(asset_id, "Asset ID")
        normalized_version = self._require_version(version)
        proof = await self._read_proof(normalized_asset_id, normalized_version)
        return self._proof_view(proof)

    async def verify_proof(
        self,
        *,
        asset_id: str,
        version: int,
        expected_hash: str,
    ) -> THVProofRegistryVerificationView:
        normalized_asset_id = self._require_hex_bytes32(asset_id, "Asset ID")
        normalized_expected_hash = self._require_hex_bytes32(
            expected_hash,
            "Expected proof hash",
            require_nonzero=False,
        )
        normalized_version = self._require_version(version)
        try:
            verified = await self._gateway.verify_proof(
                asset_id=normalized_asset_id,
                version=normalized_version,
                expected_hash=normalized_expected_hash,
            )
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof registry is unavailable for verification."
            ) from exc
        return THVProofRegistryVerificationView(
            asset_id=self._as_hex(normalized_asset_id),
            version=normalized_version,
            expected_hash=self._as_hex(normalized_expected_hash),
            verified=verified,
        )

    async def _approved_version_context(
        self,
        dossier_id: UUID,
        version_no: int,
    ) -> _ApprovedVersionContext:
        normalized_version = self._require_version(version_no)
        async with self._session.begin():
            dossier = await self._session.get(Dossier, dossier_id)
            if dossier is None:
                raise DossierNotFoundError()
            if dossier.status is not DossierStatus.APPROVED:
                raise BlockchainConflictError(
                    "A THV proof can be recorded only after dossier approval."
                )
            if dossier.current_version_no != normalized_version:
                raise BlockchainConflictError(
                    "Only the current approved dossier version can be recorded."
                )
            version = await self._session.scalar(
                select(DossierVersion).where(
                    DossierVersion.dossier_id == dossier.id,
                    DossierVersion.version_no == normalized_version,
                )
            )
            if version is None:
                raise DossierNotFoundError("Dossier version was not found.")
            canonical_hash = version.canonical_hash
            if _CANONICAL_HASH.fullmatch(canonical_hash) is None:
                raise BlockchainConflictError(
                    "Approved dossier proof hash is unavailable."
                )
            return _ApprovedVersionContext(
                dossier_id=dossier.id,
                dossier_code=dossier.code,
                dossier_title=dossier.title,
                version=version.version_no,
                canonical_hash=canonical_hash.lower(),
                version_id=version.id,
            )

    async def _required_transaction(
        self, transaction_id: UUID, *, for_update: bool = False
    ) -> BlockchainTransaction:
        statement = select(BlockchainTransaction).where(
            BlockchainTransaction.id == transaction_id,
            BlockchainTransaction.method == "recordProof",
            BlockchainTransaction.contract_address == self._contract_address,
        )
        if for_update:
            statement = statement.with_for_update()
        transaction = await self._session.scalar(statement)
        if transaction is None:
            raise BlockchainNotFoundError()
        return transaction

    async def _required_intent(
        self, intent_id: UUID, *, for_update: bool = False
    ) -> BlockchainTransactionIntent:
        statement = select(BlockchainTransactionIntent).where(
            BlockchainTransactionIntent.id == intent_id,
            BlockchainTransactionIntent.contract_address == self._contract_address,
        )
        if for_update:
            statement = statement.with_for_update()
        intent = await self._session.scalar(statement)
        if intent is None:
            raise BlockchainNotFoundError()
        return intent

    async def _require_active_wallet(
        self,
        principal: AuthPrincipal,
        connected_wallet: str,
    ) -> BlockchainWalletLink:
        address = self._require_address(connected_wallet)
        async with self._session.begin():
            link = await self._session.scalar(
                select(BlockchainWalletLink).where(
                    BlockchainWalletLink.user_id == principal.user_id,
                    BlockchainWalletLink.wallet_address == address,
                    BlockchainWalletLink.chain_id == self._chain_id,
                    BlockchainWalletLink.is_active.is_(True),
                    BlockchainWalletLink.status == BlockchainWalletLinkStatus.ACTIVE,
                )
            )
            if link is None:
                raise BlockchainForbiddenError()
            return link

    async def _require_verifier_role(self, wallet_address: str) -> None:
        try:
            is_verifier = await self._gateway.has_verifier_role(wallet_address)
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof registry signer role is unavailable."
            ) from exc
        if not is_verifier:
            raise BlockchainForbiddenError()

    async def _read_proof(self, asset_id: bytes, version: int) -> THVProofRecord:
        try:
            return await self._gateway.get_proof(asset_id, version)
        except BlockchainGatewayError as exc:
            raise BlockchainUnavailableError(
                "THV proof registry is unavailable for reading."
            ) from exc

    def _require_signer(self, principal: AuthPrincipal) -> None:
        if "SUPER_ADMIN" not in principal.roles:
            raise BlockchainForbiddenError()
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="blockchain.sign",
                compatible_roles=frozenset({"SUPER_ADMIN"}),
            ),
            BlockchainForbiddenError,
        )

    def _require_enabled(self) -> None:
        if not self._signing_enabled:
            raise BlockchainConflictError("Blockchain signing is disabled.")

    @staticmethod
    def _require_address(value: str) -> str:
        address = normalize_wallet_address(value)
        if address is None:
            raise BlockchainConflictError("Wallet address is invalid.")
        return address

    @staticmethod
    def _require_version(value: int) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= 2**64 - 1
        ):
            raise BlockchainConflictError("Proof version is invalid.")
        return value

    @staticmethod
    def _require_hex_bytes32(
        value: str,
        label: str,
        *,
        require_nonzero: bool = True,
    ) -> bytes:
        if _HEX_BYTES32.fullmatch(value) is None:
            raise BlockchainConflictError(f"{label} must be a bytes32 hex value.")
        decoded = bytes.fromhex(value.removeprefix("0x"))
        if require_nonzero and decoded == bytes(32):
            raise BlockchainConflictError(f"{label} must not be zero.")
        return decoded

    @staticmethod
    def _as_hex(value: bytes) -> str:
        return "0x" + value.hex()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _status_view(
        transaction: BlockchainTransaction,
    ) -> THVProofRegistryStatusView:
        return THVProofRegistryStatusView(
            transaction_id=transaction.id,
            status=transaction.status,
            tx_hash=transaction.tx_hash,
            confirmations=transaction.confirmations,
            error_code=transaction.error_code,
            error_message=transaction.error_message,
            confirmed_at=transaction.confirmed_at,
        )

    @classmethod
    def _proof_view(cls, proof: THVProofRecord) -> THVProofRegistryProofView:
        return THVProofRegistryProofView(
            asset_id=cls._as_hex(proof.asset_id),
            proof_hash=cls._as_hex(proof.proof_hash),
            version=proof.version,
            recorded_at=proof.recorded_at,
            signer=proof.signer,
            exists=proof.exists,
        )
