import hashlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import (
    BlockchainConflictError,
    BlockchainForbiddenError,
    BlockchainNotFoundError,
    BlockchainTransientError,
)
from app.modules.blockchain.gateway import BlockchainGateway, BlockchainGatewayError
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateVersion,
)
from app.modules.blockchain.nonce_lock import NonceLock
from app.modules.blockchain.repository import BlockchainTransactionRepository
from app.modules.blockchain.signer import TransactionSigner
from app.modules.blockchain.types import BlockchainTransactionView
from app.modules.dossiers.models import DossierStatus, DossierVersion
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.workflow import DossierWorkflowService

logger = logging.getLogger(__name__)

BLOCKCHAIN_ADMIN_ROLES = frozenset({"BLOCKCHAIN_ADMIN", "SUPER_ADMIN"})
SUPPORTED_METHODS = frozenset(
    {"issueCertificate", "updateCertificate", "revokeCertificate"}
)


class BlockchainTransactionService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: BlockchainGateway,
        signer: TransactionSigner,
        nonce_lock: NonceLock,
        network: str,
        chain_id: int,
        contract_address: str,
        required_confirmations: int,
        nonce_lock_ttl_seconds: int,
        enqueue_broadcast: Callable[[UUID], None] | None = None,
        enqueue_reconcile: Callable[[], None] | None = None,
        enqueue_certificate_issue: Callable[[UUID], None] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._gateway = gateway
        self._signer = signer
        self._nonce_lock = nonce_lock
        self._network = network
        self._chain_id = chain_id
        self._contract_address = contract_address.lower()
        self._required_confirmations = required_confirmations
        self._nonce_lock_ttl_seconds = nonce_lock_ttl_seconds
        self._enqueue_broadcast = enqueue_broadcast
        self._enqueue_reconcile = enqueue_reconcile
        self._enqueue_certificate_issue = enqueue_certificate_issue
        self._clock = clock or (lambda: datetime.now(UTC))
        self._transactions = BlockchainTransactionRepository(session)
        self._dossiers = DossierRepository(session)
        self._workflow = DossierWorkflowService(self._dossiers)

    async def request_anchor(
        self,
        *,
        dossier_id: UUID,
        dossier_version_id: UUID,
        certificate_id: UUID | None,
        method: str,
        payload: bytes,
        actor_user_id: UUID,
    ) -> BlockchainTransactionView:
        if method not in SUPPORTED_METHODS:
            raise BlockchainConflictError("Contract method is not supported.")
        payload_hash = hashlib.sha256(payload).hexdigest()
        created = False
        async with self._session.begin():
            replay = await self._transactions.find_idempotent(
                dossier_version_id=dossier_version_id,
                network=self._network,
                contract_address=self._contract_address,
                method=method,
                payload_hash=payload_hash,
            )
            if replay is not None:
                return self._view(replay)
            dossier = await self._dossiers.get_by_id(dossier_id, for_update=True)
            if dossier is None:
                raise BlockchainNotFoundError()
            version = await self._session.scalar(
                select(DossierVersion).where(
                    DossierVersion.id == dossier_version_id,
                    DossierVersion.dossier_id == dossier_id,
                )
            )
            if version is None:
                raise BlockchainConflictError(
                    "Dossier version does not belong to the dossier."
                )
            if dossier.status is not DossierStatus.PAID:
                raise BlockchainConflictError(
                    "Only a paid dossier can be anchored."
                )
            transaction = BlockchainTransaction(
                id=uuid4(),
                dossier_id=dossier_id,
                dossier_version_id=dossier_version_id,
                certificate_id=certificate_id,
                network=self._network,
                chain_id=self._chain_id,
                contract_address=self._contract_address,
                method=method,
                payload_hash=payload_hash,
                status=BlockchainTransactionStatus.CREATED,
                confirmations=0,
            )
            self._transactions.add(transaction)
            self._workflow.transition(
                dossier,
                target=DossierStatus.ANCHOR_PENDING,
                actor_user_id=actor_user_id,
                allowed_sources={DossierStatus.PAID},
                reason_code="BLOCKCHAIN_ANCHOR_REQUESTED",
            )
            await self._session.flush()
            result = self._view(transaction)
            created = True
        if created and self._enqueue_broadcast is not None:
            self._enqueue_broadcast(result.id)
        self._audit("blockchain.anchor.requested", actor_user_id, result.id)
        return result

    async def request_certificate_anchor(
        self,
        *,
        certificate_id: UUID,
        actor_user_id: UUID,
    ) -> BlockchainTransactionView:
        async with self._session.begin():
            certificate = await self._session.get(Certificate, certificate_id)
            if certificate is None:
                raise BlockchainNotFoundError()
            version = await self._session.scalar(
                select(CertificateVersion).where(
                    CertificateVersion.certificate_id == certificate_id,
                    CertificateVersion.version_no
                    == certificate.current_version_no,
                )
            )
            if version is None:
                raise BlockchainConflictError(
                    "Certificate version context is unavailable."
                )
            dossier_version = await self._session.get(
                DossierVersion,
                version.dossier_version_id,
            )
            if dossier_version is None:
                raise BlockchainConflictError(
                    "Dossier version context is unavailable."
                )
            payload = self._gateway.encode_issue_certificate(
                certificate_id=hashlib.sha256(
                    certificate.certificate_number.encode()
                ).digest(),
                dossier_hash=bytes.fromhex(dossier_version.canonical_hash),
                metadata_hash=bytes.fromhex(version.metadata_hash),
                issued_at=int(certificate.issued_at.timestamp()),
                expires_at=(
                    int(certificate.expires_at.timestamp())
                    if certificate.expires_at is not None
                    else 0
                ),
            )
            dossier_id = certificate.dossier_id
            dossier_version_id = version.dossier_version_id
        transaction = await self.request_anchor(
            dossier_id=dossier_id,
            dossier_version_id=dossier_version_id,
            certificate_id=certificate_id,
            method="issueCertificate",
            payload=payload,
            actor_user_id=actor_user_id,
        )
        async with self._session.begin():
            current_version = await self._session.scalar(
                select(CertificateVersion)
                .where(
                    CertificateVersion.certificate_id == certificate_id,
                    CertificateVersion.version_no == version.version_no,
                )
                .with_for_update()
            )
            if (
                current_version is not None
                and current_version.blockchain_transaction_id is None
            ):
                current_version.blockchain_transaction_id = transaction.id
        return transaction

    async def broadcast(self, transaction_id: UUID, payload: bytes) -> None:
        should_broadcast = False
        async with self._session.begin():
            transaction = await self._required(transaction_id, for_update=True)
            if transaction.status in {
                BlockchainTransactionStatus.BROADCAST,
                BlockchainTransactionStatus.CONFIRMED,
            }:
                return
            if transaction.status not in {
                BlockchainTransactionStatus.CREATED,
                BlockchainTransactionStatus.FAILED,
            }:
                raise BlockchainConflictError(
                    "Blockchain transaction is already being processed."
                )
            if hashlib.sha256(payload).hexdigest() != transaction.payload_hash:
                raise BlockchainConflictError(
                    "Blockchain transaction payload does not match."
                )
            transaction.status = BlockchainTransactionStatus.SIGNING
            transaction.error_code = None
            transaction.error_message = None
            should_broadcast = True
        if not should_broadcast:
            return

        lock_key = f"blockchain:nonce:{self._network}:{self._signer.address.lower()}"
        token: str | None = None
        try:
            token = await self._nonce_lock.acquire(
                lock_key,
                ttl_seconds=self._nonce_lock_ttl_seconds,
            )
            if token is None:
                raise BlockchainGatewayError("Signer nonce is currently locked.")
            nonce = await self._gateway.pending_nonce(self._signer.address)
            gas = await self._gateway.estimate_gas(
                signer=self._signer.address,
                payload=payload,
            )
            gas_price = await self._gateway.gas_price()
            raw_transaction = self._signer.sign(
                {
                    "chainId": self._chain_id,
                    "nonce": nonce,
                    "gas": gas,
                    "gasPrice": gas_price,
                    "to": self._contract_address,
                    "data": f"0x{payload.hex()}",
                    "value": 0,
                }
            )
            tx_hash = await self._gateway.broadcast(raw_transaction)
        except (BlockchainGatewayError, OSError, RuntimeError) as exc:
            await self._record_failure(
                transaction_id,
                error_code="RPC_FAILURE",
                error_message=str(exc),
            )
            raise BlockchainTransientError("Blockchain broadcast failed.") from exc
        finally:
            if token is not None:
                await self._nonce_lock.release(lock_key, token)

        async with self._session.begin():
            transaction = await self._required(transaction_id, for_update=True)
            if transaction.status is BlockchainTransactionStatus.SIGNING:
                transaction.nonce = nonce
                transaction.tx_hash = tx_hash
                transaction.status = BlockchainTransactionStatus.BROADCAST
                transaction.broadcast_at = self._clock()
        logger.info(
            "blockchain.transaction.broadcast",
            extra={"transaction_id": str(transaction_id), "tx_hash": tx_hash},
        )

    async def confirm(self, transaction_id: UUID) -> None:
        certificate_dossier_id: UUID | None = None
        async with self._session.begin():
            transaction = await self._required(transaction_id)
            if transaction.status is BlockchainTransactionStatus.CONFIRMED:
                return
            if (
                transaction.status is not BlockchainTransactionStatus.BROADCAST
                or transaction.tx_hash is None
            ):
                return
            tx_hash = transaction.tx_hash
        try:
            receipt = await self._gateway.receipt(tx_hash)
            if receipt is None:
                return
            if not receipt.succeeded:
                await self._record_failure(
                    transaction_id,
                    error_code="TRANSACTION_REVERTED",
                    error_message="Blockchain transaction reverted.",
                )
                return
            latest_block = await self._gateway.latest_block_number()
            confirmations = max(0, latest_block - receipt.block_number + 1)
        except BlockchainGatewayError as exc:
            raise BlockchainTransientError(
                "Blockchain confirmation lookup failed."
            ) from exc

        async with self._session.begin():
            transaction = await self._required(transaction_id, for_update=True)
            if transaction.status is not BlockchainTransactionStatus.BROADCAST:
                return
            transaction.confirmations = confirmations
            if confirmations >= self._required_confirmations:
                transaction.status = BlockchainTransactionStatus.CONFIRMED
                transaction.confirmed_at = self._clock()
                dossier = await self._dossiers.get_by_id(
                    transaction.dossier_id,
                    for_update=True,
                )
                if (
                    dossier is not None
                    and dossier.status is DossierStatus.ANCHOR_PENDING
                ):
                    self._workflow.transition(
                        dossier,
                        target=DossierStatus.ANCHORED,
                        actor_user_id=dossier.owner_user_id,
                        allowed_sources={DossierStatus.ANCHOR_PENDING},
                        reason_code="BLOCKCHAIN_ANCHOR_CONFIRMED",
                    )
                    if transaction.certificate_id is not None:
                        certificate_dossier_id = dossier.id
        if (
            certificate_dossier_id is not None
            and self._enqueue_certificate_issue is not None
        ):
            self._enqueue_certificate_issue(certificate_dossier_id)

    async def list_admin(
        self,
        principal: AuthPrincipal,
        *,
        status: BlockchainTransactionStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[BlockchainTransactionView, ...], int]:
        self._require_admin(principal)
        async with self._session.begin():
            rows, total = await self._transactions.list(
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return tuple(self._view(row) for row in rows), total

    async def retry_admin(
        self,
        principal: AuthPrincipal,
        transaction_id: UUID,
    ) -> BlockchainTransactionView:
        self._require_admin(principal)
        async with self._session.begin():
            transaction = await self._required(transaction_id, for_update=True)
            if transaction.status is not BlockchainTransactionStatus.FAILED:
                raise BlockchainConflictError(
                    "Only a failed blockchain transaction can be retried."
                )
            transaction.status = BlockchainTransactionStatus.CREATED
            transaction.error_code = None
            transaction.error_message = None
            await self._session.flush()
            result = self._view(transaction)
        if self._enqueue_broadcast is not None:
            self._enqueue_broadcast(result.id)
        self._audit("blockchain.transaction.retry", principal.user_id, result.id)
        return result

    async def reconcile_admin(self, principal: AuthPrincipal) -> None:
        self._require_admin(principal)
        if self._enqueue_reconcile is not None:
            self._enqueue_reconcile()
        self._audit("blockchain.reconcile.requested", principal.user_id, None)

    async def reconcile(self, *, limit: int = 100) -> int:
        async with self._session.begin():
            rows = await self._transactions.list_broadcast(limit=limit)
            transaction_ids = tuple(row.id for row in rows)
        for transaction_id in transaction_ids:
            await self.confirm(transaction_id)
        return len(transaction_ids)

    async def resolve_payload(self, transaction_id: UUID) -> bytes:
        async with self._session.begin():
            transaction = await self._required(transaction_id)
            if transaction.certificate_id is None:
                raise BlockchainConflictError(
                    "Transaction certificate context is unavailable."
                )
            certificate = await self._session.get(
                Certificate,
                transaction.certificate_id,
            )
            version = await self._session.scalar(
                select(CertificateVersion).where(
                    CertificateVersion.certificate_id == transaction.certificate_id,
                    CertificateVersion.dossier_version_id
                    == transaction.dossier_version_id,
                )
            )
            dossier_version = await self._session.get(
                DossierVersion,
                transaction.dossier_version_id,
            )
            if certificate is None or version is None or dossier_version is None:
                raise BlockchainConflictError(
                    "Transaction payload context is incomplete."
                )
            certificate_key = hashlib.sha256(
                certificate.certificate_number.encode()
            ).digest()
            dossier_hash = bytes.fromhex(dossier_version.canonical_hash)
            metadata_hash = bytes.fromhex(version.metadata_hash)
            if transaction.method == "issueCertificate":
                expires_at = (
                    int(certificate.expires_at.timestamp())
                    if certificate.expires_at is not None
                    else 0
                )
                return self._gateway.encode_issue_certificate(
                    certificate_id=certificate_key,
                    dossier_hash=dossier_hash,
                    metadata_hash=metadata_hash,
                    issued_at=int(certificate.issued_at.timestamp()),
                    expires_at=expires_at,
                )
            if transaction.method == "updateCertificate":
                return self._gateway.encode_update_certificate(
                    certificate_id=certificate_key,
                    dossier_hash=dossier_hash,
                    metadata_hash=metadata_hash,
                    version=version.version_no,
                )
            raise BlockchainConflictError(
                "Revocation payload must be supplied by the certificate service."
            )

    async def _record_failure(
        self,
        transaction_id: UUID,
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        async with self._session.begin():
            transaction = await self._required(transaction_id, for_update=True)
            if transaction.status is BlockchainTransactionStatus.CONFIRMED:
                return
            transaction.status = BlockchainTransactionStatus.FAILED
            transaction.error_code = error_code
            transaction.error_message = error_message[:2_000]

    async def _required(
        self,
        transaction_id: UUID,
        *,
        for_update: bool = False,
    ) -> BlockchainTransaction:
        transaction = await self._transactions.get(
            transaction_id,
            for_update=for_update,
        )
        if transaction is None:
            raise BlockchainNotFoundError()
        return transaction

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        if not BLOCKCHAIN_ADMIN_ROLES.intersection(principal.roles):
            raise BlockchainForbiddenError()

    @staticmethod
    def _view(transaction: BlockchainTransaction) -> BlockchainTransactionView:
        return BlockchainTransactionView(
            id=transaction.id,
            dossier_id=transaction.dossier_id,
            dossier_version_id=transaction.dossier_version_id,
            certificate_id=transaction.certificate_id,
            network=transaction.network,
            chain_id=transaction.chain_id,
            contract_address=transaction.contract_address,
            method=transaction.method,
            payload_hash=transaction.payload_hash,
            tx_hash=transaction.tx_hash,
            nonce=transaction.nonce,
            status=transaction.status,
            confirmations=transaction.confirmations,
            error_code=transaction.error_code,
            error_message=transaction.error_message,
            broadcast_at=transaction.broadcast_at,
            confirmed_at=transaction.confirmed_at,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
        )

    @staticmethod
    def _audit(
        action: str,
        actor_user_id: UUID,
        transaction_id: UUID | None,
    ) -> None:
        logger.info(
            action,
            extra={
                "actor_user_id": str(actor_user_id),
                "transaction_id": (
                    str(transaction_id) if transaction_id is not None else None
                ),
            },
        )
