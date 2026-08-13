import hashlib
import inspect
import logging
import secrets
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.document_evidence import (
    ZERO_HASH,
    build_document_evidence_commitment,
)
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
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
    DocumentBlockchainEvidence,
    DocumentEvidenceStatus,
)
from app.modules.blockchain.nonce_lock import NonceLock
from app.modules.blockchain.repository import BlockchainTransactionRepository
from app.modules.blockchain.signer import TransactionSigner
from app.modules.blockchain.types import (
    BlockchainTransactionView,
    DocumentEvidenceView,
)
from app.modules.dossiers.models import (
    DocumentHashAnchor,
    DocumentHashClaim,
    DossierStatus,
    DossierVersion,
)
from app.modules.dossiers.provenance import version_has_trusted_provenance
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.workflow import DossierWorkflowService

logger = logging.getLogger(__name__)

BLOCKCHAIN_ADMIN_ROLES = frozenset({"BLOCKCHAIN_ADMIN", "SUPER_ADMIN"})
SUPPORTED_METHODS = frozenset(
    {
        "issueCertificate",
        "updateCertificate",
        "revokeCertificate",
        "anchorDocumentEvidence",
    }
)
EXPECTED_RECEIPT_EVENTS = {
    "issueCertificate": "CertificateIssued",
    "updateCertificate": "CertificateUpdated",
    "revokeCertificate": "CertificateRevoked",
    "anchorDocumentEvidence": "DocumentEvidenceAnchored",
}

DOCUMENT_EVIDENCE_ELIGIBLE_STATUSES = frozenset(
    {
        DossierStatus.PAID,
        DossierStatus.ANCHOR_PENDING,
        DossierStatus.ANCHORED,
        DossierStatus.CERTIFICATE_ISSUED,
        DossierStatus.PUBLISHED,
    }
)

EnqueueById = Callable[[UUID], Awaitable[None] | None]
EnqueueSignal = Callable[[], Awaitable[None] | None]


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
        enqueue_broadcast: EnqueueById | None = None,
        enqueue_reconcile: EnqueueSignal | None = None,
        enqueue_certificate_issue: EnqueueById | None = None,
        enqueue_certificate_version: EnqueueById | None = None,
        clock: Callable[[], datetime] | None = None,
        submitter_reference_factory: Callable[[], str] | None = None,
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
        self._enqueue_certificate_version = enqueue_certificate_version
        self._clock = clock or (lambda: datetime.now(UTC))
        self._submitter_reference_factory = submitter_reference_factory or (
            lambda: secrets.token_hex(32)
        )
        self._transactions = BlockchainTransactionRepository(session)
        self._audit_service = AuditService(session)
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
            evidence_rows = await self._dossiers.list_evidences(
                dossier_id,
                version_id=dossier_version_id,
            )
            if not version_has_trusted_provenance(version, evidence_rows):
                raise BlockchainConflictError(
                    "Evidence integrity must be reverified before anchoring."
                )
            if replay is not None:
                return self._view(replay)
            if dossier.status is not DossierStatus.PAID:
                raise BlockchainConflictError("Only a paid dossier can be anchored.")
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
            self._audit(
                "blockchain.anchor.requested",
                transaction.id,
                actor_user_id=actor_user_id,
                status=BlockchainTransactionStatus.CREATED,
            )
            await self._session.flush()
            result = self._view(transaction)
            created = True
        if created and self._enqueue_broadcast is not None:
            await self._invoke(self._enqueue_broadcast, result.id)
        return result

    async def request_document_evidence(
        self,
        *,
        document_hash_claim_id: UUID,
        actor_user_id: UUID,
        predecessor_evidence_id: UUID | None = None,
    ) -> DocumentEvidenceView:
        created = False
        async with self._session.begin():
            replay = await self._session.scalar(
                select(DocumentBlockchainEvidence)
                .where(
                    DocumentBlockchainEvidence.document_hash_claim_id
                    == document_hash_claim_id
                )
                .with_for_update()
            )
            if replay is not None:
                transaction = await self._document_evidence_transaction(replay.id)
                return await self._document_evidence_view(replay, transaction)

            claim = await self._session.scalar(
                select(DocumentHashClaim)
                .where(DocumentHashClaim.id == document_hash_claim_id)
                .with_for_update()
            )
            if claim is None:
                raise BlockchainNotFoundError()
            dossier = await self._dossiers.get_by_id(claim.dossier_id, for_update=True)
            if dossier is None:
                raise BlockchainNotFoundError()
            if dossier.status not in DOCUMENT_EVIDENCE_ELIGIBLE_STATUSES:
                raise BlockchainConflictError(
                    "Document evidence is not approved for blockchain anchoring."
                )
            anchor = await self._session.get(DocumentHashAnchor, claim.anchor_id)
            if anchor is None:
                raise BlockchainConflictError(
                    "Trusted document hash context is unavailable."
                )

            predecessor: DocumentBlockchainEvidence | None = None
            if predecessor_evidence_id is not None:
                predecessor = await self._session.scalar(
                    select(DocumentBlockchainEvidence)
                    .where(DocumentBlockchainEvidence.id == predecessor_evidence_id)
                    .with_for_update()
                )
                if (
                    predecessor is None
                    or predecessor.dossier_id != claim.dossier_id
                    or predecessor.status is not DocumentEvidenceStatus.CONFIRMED
                ):
                    raise BlockchainConflictError(
                        "Document evidence predecessor is unavailable."
                    )
            version_no = predecessor.version_no + 1 if predecessor is not None else 1
            recorded_at = claim.claimed_at
            if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
                recorded_at = recorded_at.replace(tzinfo=UTC)
            submitter_reference = self._submitter_reference_factory()
            commitment = build_document_evidence_commitment(
                document_claim_id=claim.id,
                document_sha256=anchor.sha256,
                version=version_no,
                submitter_reference=submitter_reference,
                previous_evidence_key=(
                    predecessor.evidence_key if predecessor is not None else None
                ),
                recorded_at=recorded_at,
            )
            evidence = DocumentBlockchainEvidence(
                id=uuid4(),
                document_hash_claim_id=claim.id,
                dossier_id=claim.dossier_id,
                dossier_version_id=claim.dossier_version_id,
                evidence_key=commitment.evidence_key,
                commitment=commitment.commitment,
                submitter_reference=submitter_reference,
                version_no=version_no,
                predecessor_evidence_id=(
                    predecessor.id if predecessor is not None else None
                ),
                recorded_at=recorded_at,
                status=DocumentEvidenceStatus.QUEUED,
            )
            self._session.add(evidence)
            await self._session.flush()
            payload = self._gateway.encode_anchor_document_evidence(
                evidence_key=bytes.fromhex(evidence.evidence_key),
                commitment=bytes.fromhex(evidence.commitment),
                previous_evidence_key=(
                    bytes.fromhex(predecessor.evidence_key)
                    if predecessor is not None
                    else ZERO_HASH
                ),
                version=evidence.version_no,
                recorded_at=commitment.recorded_at_epoch,
            )
            transaction = BlockchainTransaction(
                id=uuid4(),
                dossier_id=claim.dossier_id,
                dossier_version_id=claim.dossier_version_id,
                document_evidence_id=evidence.id,
                network=self._network,
                chain_id=self._chain_id,
                contract_address=self._contract_address,
                method="anchorDocumentEvidence",
                payload_hash=hashlib.sha256(payload).hexdigest(),
                status=BlockchainTransactionStatus.CREATED,
                confirmations=0,
            )
            self._transactions.add(transaction)
            self._audit(
                "blockchain.document_evidence.requested",
                transaction.id,
                actor_user_id=actor_user_id,
                status=BlockchainTransactionStatus.CREATED,
            )
            await self._session.flush()
            result = await self._document_evidence_view(evidence, transaction)
            created = True
        if created and self._enqueue_broadcast is not None:
            await self._invoke(self._enqueue_broadcast, result.transaction_id)
        return result

    async def request_document_evidences_for_version(
        self,
        *,
        dossier_version_id: UUID,
        actor_user_id: UUID,
    ) -> tuple[DocumentEvidenceView, ...]:
        async with self._session.begin():
            claim_ids = tuple(
                await self._session.scalars(
                    select(DocumentHashClaim.id)
                    .where(DocumentHashClaim.dossier_version_id == dossier_version_id)
                    .order_by(DocumentHashClaim.claimed_at, DocumentHashClaim.id)
                )
            )
        results = []
        for claim_id in claim_ids:
            results.append(
                await self.request_document_evidence(
                    document_hash_claim_id=claim_id,
                    actor_user_id=actor_user_id,
                )
            )
        return tuple(results)

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
                    CertificateVersion.version_no == certificate.current_version_no,
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
                raise BlockchainConflictError("Dossier version context is unavailable.")
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
        await self.request_document_evidences_for_version(
            dossier_version_id=dossier_version_id,
            actor_user_id=actor_user_id,
        )
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

    async def request_certificate_update_anchor(
        self,
        *,
        certificate_version_id: UUID,
        actor_user_id: UUID,
    ) -> BlockchainTransactionView:
        """Approve and enqueue one immutable certificate correction.

        The existing ACTIVE version remains public until this transaction has
        enough canonical confirmations. Replays resolve to the same transaction.
        """
        async with self._session.begin():
            requested_version = await self._session.get(
                CertificateVersion,
                certificate_version_id,
            )
            if requested_version is None:
                raise BlockchainNotFoundError()
            requested_dossier_version_id = requested_version.dossier_version_id
        await self.request_document_evidences_for_version(
            dossier_version_id=requested_dossier_version_id,
            actor_user_id=actor_user_id,
        )
        created = False
        async with self._session.begin():
            version = await self._session.scalar(
                select(CertificateVersion)
                .where(CertificateVersion.id == certificate_version_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if version is None:
                raise BlockchainNotFoundError()
            certificate = await self._session.scalar(
                select(Certificate)
                .where(Certificate.id == version.certificate_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if certificate is None:
                raise BlockchainConflictError(
                    "Certificate version context is unavailable."
                )
            if certificate.status is not CertificateStatus.ACTIVE:
                raise BlockchainConflictError(
                    "Only an active certificate can be updated."
                )
            if version.status not in {
                CertificateVersionStatus.PENDING_APPROVAL,
                CertificateVersionStatus.ANCHOR_PENDING,
                CertificateVersionStatus.FAILED,
            }:
                raise BlockchainConflictError(
                    "Certificate correction is not ready for anchoring."
                )
            if (
                version.status is CertificateVersionStatus.PENDING_APPROVAL
                and version.requested_by == actor_user_id
            ):
                raise BlockchainForbiddenError()
            dossier_version = await self._session.get(
                DossierVersion,
                version.dossier_version_id,
            )
            if dossier_version is None:
                raise BlockchainConflictError("Dossier version context is unavailable.")
            evidence_rows = await self._dossiers.list_evidences(
                certificate.dossier_id,
                version_id=dossier_version.id,
            )
            if not version_has_trusted_provenance(
                dossier_version,
                evidence_rows,
            ):
                raise BlockchainConflictError(
                    "Correction evidence integrity must be reverified."
                )
            payload = self._gateway.encode_update_certificate(
                certificate_id=hashlib.sha256(
                    certificate.certificate_number.encode()
                ).digest(),
                dossier_hash=bytes.fromhex(dossier_version.canonical_hash),
                metadata_hash=bytes.fromhex(version.metadata_hash),
                version=version.version_no,
            )
            payload_hash = hashlib.sha256(payload).hexdigest()
            replay = await self._transactions.find_idempotent(
                dossier_version_id=version.dossier_version_id,
                network=self._network,
                contract_address=self._contract_address,
                method="updateCertificate",
                payload_hash=payload_hash,
            )
            if replay is not None:
                if version.blockchain_transaction_id is None:
                    version.blockchain_transaction_id = replay.id
                    self._audit(
                        "blockchain.certificate_update.requested",
                        replay.id,
                        actor_user_id=actor_user_id,
                        status=replay.status,
                    )
                return self._view(replay)
            if version.status is not CertificateVersionStatus.PENDING_APPROVAL:
                raise BlockchainConflictError(
                    "Certificate correction transaction context is unavailable."
                )
            transaction = BlockchainTransaction(
                id=uuid4(),
                dossier_id=certificate.dossier_id,
                dossier_version_id=version.dossier_version_id,
                certificate_id=certificate.id,
                network=self._network,
                chain_id=self._chain_id,
                contract_address=self._contract_address,
                method="updateCertificate",
                payload_hash=payload_hash,
                status=BlockchainTransactionStatus.CREATED,
                confirmations=0,
            )
            self._transactions.add(transaction)
            version.status = CertificateVersionStatus.ANCHOR_PENDING
            version.decided_by = actor_user_id
            version.decided_at = self._clock()
            version.blockchain_transaction_id = transaction.id
            self._audit(
                "blockchain.certificate_update.requested",
                transaction.id,
                actor_user_id=actor_user_id,
                status=BlockchainTransactionStatus.CREATED,
            )
            await self._session.flush()
            result = self._view(transaction)
            created = True
        if created and self._enqueue_broadcast is not None:
            await self._invoke(self._enqueue_broadcast, result.id)
        return result

    async def request_certificate_revocation(
        self,
        *,
        certificate_id: UUID,
        reason: str,
        actor_user_id: UUID,
    ) -> BlockchainTransactionView:
        normalized_reason = " ".join(reason.split())
        if not 20 <= len(normalized_reason) <= 2_000:
            raise BlockchainConflictError(
                "Revocation reason must contain between 20 and 2000 characters."
            )
        reason_hash = hashlib.sha256(normalized_reason.encode("utf-8")).hexdigest()
        created = False
        async with self._session.begin():
            certificate = await self._session.scalar(
                select(Certificate)
                .where(Certificate.id == certificate_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if certificate is None:
                raise BlockchainNotFoundError()
            if certificate.status is CertificateStatus.REVOKED:
                raise BlockchainConflictError("Certificate is already revoked.")
            open_version = await self._session.scalar(
                select(CertificateVersion.id).where(
                    CertificateVersion.certificate_id == certificate.id,
                    CertificateVersion.status.in_(
                        (
                            CertificateVersionStatus.PENDING_APPROVAL,
                            CertificateVersionStatus.ANCHOR_PENDING,
                            CertificateVersionStatus.FAILED,
                        )
                    ),
                )
            )
            if open_version is not None:
                raise BlockchainConflictError(
                    "Resolve the open certificate correction before revocation."
                )
            version = await self._session.scalar(
                select(CertificateVersion).where(
                    CertificateVersion.certificate_id == certificate.id,
                    CertificateVersion.version_no == certificate.current_version_no,
                )
            )
            if version is None or version.status is not CertificateVersionStatus.ACTIVE:
                raise BlockchainConflictError(
                    "Active certificate version context is unavailable."
                )
            if certificate.revocation_transaction_id is not None:
                replay = await self._transactions.get(
                    certificate.revocation_transaction_id
                )
                if replay is None or certificate.revocation_reason_hash != reason_hash:
                    raise BlockchainConflictError(
                        "A certificate revocation is already being processed."
                    )
                return self._view(replay)
            payload = self._gateway.encode_revoke_certificate(
                certificate_id=hashlib.sha256(
                    certificate.certificate_number.encode()
                ).digest(),
                reason_hash=bytes.fromhex(reason_hash),
            )
            payload_hash = hashlib.sha256(payload).hexdigest()
            replay = await self._transactions.find_idempotent(
                dossier_version_id=version.dossier_version_id,
                network=self._network,
                contract_address=self._contract_address,
                method="revokeCertificate",
                payload_hash=payload_hash,
            )
            if replay is None:
                replay = BlockchainTransaction(
                    id=uuid4(),
                    dossier_id=certificate.dossier_id,
                    dossier_version_id=version.dossier_version_id,
                    certificate_id=certificate.id,
                    network=self._network,
                    chain_id=self._chain_id,
                    contract_address=self._contract_address,
                    method="revokeCertificate",
                    payload_hash=payload_hash,
                    status=BlockchainTransactionStatus.CREATED,
                    confirmations=0,
                )
                self._transactions.add(replay)
                created = True
            certificate.revocation_reason_hash = reason_hash
            certificate.revocation_transaction_id = replay.id
            self._audit(
                "blockchain.certificate_revocation.requested",
                replay.id,
                actor_user_id=actor_user_id,
                status=replay.status,
            )
            await self._session.flush()
            result = self._view(replay)
        if created and self._enqueue_broadcast is not None:
            await self._invoke(self._enqueue_broadcast, result.id)
        return result

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
            raw_transaction = await self._signer.sign(
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
                error_message="Blockchain RPC request failed.",
                actor_service="blockchain-broadcast-worker",
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
                if transaction.document_evidence_id is not None:
                    evidence = await self._session.get(
                        DocumentBlockchainEvidence,
                        transaction.document_evidence_id,
                    )
                    if evidence is not None:
                        evidence.status = DocumentEvidenceStatus.BROADCAST
                self._audit(
                    "blockchain.transaction.broadcasted",
                    transaction.id,
                    actor_service="blockchain-broadcast-worker",
                    status=BlockchainTransactionStatus.BROADCAST,
                )
        logger.info(
            "blockchain.transaction.broadcast",
            extra={"transaction_id": str(transaction_id), "tx_hash": tx_hash},
        )

    async def confirm(self, transaction_id: UUID) -> None:
        certificate_dossier_id: UUID | None = None
        confirmed_version_id: UUID | None = None
        async with self._session.begin():
            transaction = await self._required(transaction_id)
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
            method = transaction.method
            already_confirmed = (
                transaction.status is BlockchainTransactionStatus.CONFIRMED
            )
        try:
            receipt = await self._gateway.receipt(tx_hash)
            if receipt is None:
                if already_confirmed:
                    await self._record_reconciliation_mismatch(
                        transaction_id,
                        "Confirmed transaction receipt is no longer available.",
                    )
                return
            if not receipt.succeeded:
                if already_confirmed:
                    await self._record_reconciliation_mismatch(
                        transaction_id,
                        "Confirmed transaction now reports a reverted receipt.",
                    )
                else:
                    await self._record_failure(
                        transaction_id,
                        error_code="TRANSACTION_REVERTED",
                        error_message="Blockchain transaction reverted.",
                        actor_service="blockchain-confirmation-worker",
                    )
                return
            expected_event = EXPECTED_RECEIPT_EVENTS[method]
            if (
                receipt.transaction_hash.lower() != tx_hash.lower()
                or receipt.contract_address.lower() != self._contract_address
                or expected_event not in receipt.event_names
            ):
                if already_confirmed:
                    await self._record_reconciliation_mismatch(
                        transaction_id,
                        "Receipt contract, transaction hash or event does not match.",
                    )
                else:
                    await self._record_failure(
                        transaction_id,
                        error_code="RECEIPT_MISMATCH",
                        error_message=(
                            "Receipt contract, transaction hash or event does not "
                            "match."
                        ),
                        actor_service="blockchain-confirmation-worker",
                    )
                return
            canonical_block_hash = await self._gateway.block_hash(receipt.block_number)
            if canonical_block_hash.lower() != receipt.block_hash.lower():
                await self._record_reconciliation_mismatch(
                    transaction_id,
                    "Receipt block is no longer canonical.",
                )
                return
            latest_block = await self._gateway.latest_block_number()
            confirmations = max(0, latest_block - receipt.block_number + 1)
            if method == "anchorDocumentEvidence":
                async with self._session.begin():
                    transaction = await self._required(transaction_id)
                    evidence = (
                        await self._session.get(
                            DocumentBlockchainEvidence,
                            transaction.document_evidence_id,
                        )
                        if transaction.document_evidence_id is not None
                        else None
                    )
                if evidence is None:
                    await self._record_reconciliation_mismatch(
                        transaction_id,
                        "Document evidence context is unavailable.",
                    )
                    return
                chain_record = await self._gateway.get_document_evidence(
                    bytes.fromhex(evidence.evidence_key)
                )
                expected_predecessor = ZERO_HASH
                if evidence.predecessor_evidence_id is not None:
                    async with self._session.begin():
                        predecessor = await self._session.get(
                            DocumentBlockchainEvidence,
                            evidence.predecessor_evidence_id,
                        )
                    if predecessor is None:
                        await self._record_reconciliation_mismatch(
                            transaction_id,
                            "Document evidence predecessor is unavailable.",
                        )
                        return
                    expected_predecessor = bytes.fromhex(predecessor.evidence_key)
                recorded_at = evidence.recorded_at
                if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
                    recorded_at = recorded_at.replace(tzinfo=UTC)
                if (
                    chain_record.commitment != bytes.fromhex(evidence.commitment)
                    or chain_record.previous_evidence_key != expected_predecessor
                    or chain_record.version != evidence.version_no
                    or chain_record.recorded_at != int(recorded_at.timestamp())
                ):
                    await self._record_reconciliation_mismatch(
                        transaction_id,
                        "Document evidence chain state does not match.",
                    )
                    return
        except BlockchainGatewayError as exc:
            raise BlockchainTransientError(
                "Blockchain confirmation lookup failed."
            ) from exc

        async with self._session.begin():
            transaction = await self._required(transaction_id, for_update=True)
            if transaction.status not in {
                BlockchainTransactionStatus.BROADCAST,
                BlockchainTransactionStatus.CONFIRMED,
            }:
                return
            transaction.confirmations = confirmations
            transaction.receipt_block_number = receipt.block_number
            transaction.receipt_block_hash = receipt.block_hash
            transaction.receipt_event_name = expected_event
            transaction.error_code = None
            transaction.error_message = None
            if transaction.status is BlockchainTransactionStatus.CONFIRMED:
                return
            if confirmations >= self._required_confirmations:
                transaction.status = BlockchainTransactionStatus.CONFIRMED
                transaction.confirmed_at = self._clock()
                if transaction.method == "issueCertificate":
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
                elif transaction.method == "updateCertificate":
                    confirmed_version_id = await self._promote_confirmed_version(
                        transaction
                    )
                elif transaction.method == "revokeCertificate":
                    await self._confirm_certificate_revocation(transaction)
                elif transaction.method == "anchorDocumentEvidence":
                    if transaction.document_evidence_id is None:
                        raise BlockchainConflictError(
                            "Confirmed document evidence context is unavailable."
                        )
                    evidence = await self._session.get(
                        DocumentBlockchainEvidence,
                        transaction.document_evidence_id,
                    )
                    if evidence is None:
                        raise BlockchainConflictError(
                            "Confirmed document evidence context is unavailable."
                        )
                    evidence.status = DocumentEvidenceStatus.CONFIRMED
                self._audit(
                    "blockchain.transaction.confirmed",
                    transaction.id,
                    actor_service="blockchain-confirmation-worker",
                    status=BlockchainTransactionStatus.CONFIRMED,
                    confirmations=confirmations,
                )
        if (
            certificate_dossier_id is not None
            and self._enqueue_certificate_issue is not None
        ):
            await self._invoke(
                self._enqueue_certificate_issue,
                certificate_dossier_id,
            )
        if (
            confirmed_version_id is not None
            and self._enqueue_certificate_version is not None
        ):
            await self._invoke(
                self._enqueue_certificate_version,
                confirmed_version_id,
            )

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

    async def list_document_evidences_admin(
        self,
        principal: AuthPrincipal,
        *,
        status: DocumentEvidenceStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[DocumentEvidenceView, ...], int]:
        self._require_admin(principal)
        async with self._session.begin():
            rows, total = await self._transactions.list_document_evidences(
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return (
                tuple(
                    [
                        await self._document_evidence_view(evidence, transaction)
                        for evidence, transaction in rows
                    ]
                ),
                total,
            )

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
            if transaction.method == "updateCertificate":
                version = await self._session.scalar(
                    select(CertificateVersion).where(
                        CertificateVersion.blockchain_transaction_id == transaction.id
                    )
                )
                if (
                    version is not None
                    and version.status is CertificateVersionStatus.FAILED
                ):
                    version.status = CertificateVersionStatus.ANCHOR_PENDING
            if transaction.document_evidence_id is not None:
                evidence = await self._session.get(
                    DocumentBlockchainEvidence,
                    transaction.document_evidence_id,
                )
                if evidence is not None:
                    evidence.status = DocumentEvidenceStatus.QUEUED
            await self._session.flush()
            await self._session.refresh(transaction)
            result = self._view(transaction)
            self._audit(
                "blockchain.transaction.retry",
                transaction.id,
                actor_user_id=principal.user_id,
                status=BlockchainTransactionStatus.CREATED,
            )
        if self._enqueue_broadcast is not None:
            await self._invoke(self._enqueue_broadcast, result.id)
        return result

    async def reconcile_admin(self, principal: AuthPrincipal) -> None:
        self._require_admin(principal)
        async with self._session.begin():
            self._audit(
                "blockchain.reconcile.requested",
                None,
                actor_user_id=principal.user_id,
            )
        if self._enqueue_reconcile is not None:
            await self._invoke(self._enqueue_reconcile)

    @staticmethod
    async def _invoke(
        callback: Callable[..., Awaitable[None] | None], *args: object
    ) -> None:
        result = callback(*args)
        if inspect.isawaitable(result):
            await result

    async def reconcile(self, *, limit: int = 100) -> int:
        async with self._session.begin():
            rows = await self._transactions.list_reconcilable(limit=limit)
            transaction_ids = tuple(row.id for row in rows)
        for transaction_id in transaction_ids:
            await self.confirm(transaction_id)
        return len(transaction_ids)

    async def resolve_payload(self, transaction_id: UUID) -> bytes:
        async with self._session.begin():
            transaction = await self._required(transaction_id)
            if transaction.method == "anchorDocumentEvidence":
                if transaction.document_evidence_id is None:
                    raise BlockchainConflictError(
                        "Document evidence transaction context is unavailable."
                    )
                evidence = await self._session.get(
                    DocumentBlockchainEvidence,
                    transaction.document_evidence_id,
                )
                if evidence is None:
                    raise BlockchainConflictError(
                        "Document evidence transaction context is unavailable."
                    )
                claim = await self._session.get(
                    DocumentHashClaim,
                    evidence.document_hash_claim_id,
                )
                anchor = (
                    await self._session.get(DocumentHashAnchor, claim.anchor_id)
                    if claim is not None
                    else None
                )
                if claim is None or anchor is None:
                    raise BlockchainConflictError(
                        "Trusted document hash context is unavailable."
                    )
                predecessor_key: str | None = None
                if evidence.predecessor_evidence_id is not None:
                    predecessor = await self._session.get(
                        DocumentBlockchainEvidence,
                        evidence.predecessor_evidence_id,
                    )
                    if predecessor is None:
                        raise BlockchainConflictError(
                            "Document evidence predecessor context is unavailable."
                        )
                    predecessor_key = predecessor.evidence_key
                recorded_at = evidence.recorded_at
                if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
                    recorded_at = recorded_at.replace(tzinfo=UTC)
                commitment = build_document_evidence_commitment(
                    document_claim_id=claim.id,
                    document_sha256=anchor.sha256,
                    version=evidence.version_no,
                    submitter_reference=evidence.submitter_reference,
                    previous_evidence_key=predecessor_key,
                    recorded_at=recorded_at,
                )
                if (
                    commitment.evidence_key != evidence.evidence_key
                    or commitment.commitment != evidence.commitment
                ):
                    raise BlockchainConflictError(
                        "Document evidence commitment does not match."
                    )
                return self._gateway.encode_anchor_document_evidence(
                    evidence_key=bytes.fromhex(evidence.evidence_key),
                    commitment=bytes.fromhex(evidence.commitment),
                    previous_evidence_key=(
                        bytes.fromhex(predecessor_key)
                        if predecessor_key is not None
                        else ZERO_HASH
                    ),
                    version=evidence.version_no,
                    recorded_at=commitment.recorded_at_epoch,
                )
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
            if transaction.method == "revokeCertificate":
                if certificate.revocation_reason_hash is None:
                    raise BlockchainConflictError(
                        "Revocation reason context is unavailable."
                    )
                return self._gateway.encode_revoke_certificate(
                    certificate_id=certificate_key,
                    reason_hash=bytes.fromhex(certificate.revocation_reason_hash),
                )
            raise BlockchainConflictError("Transaction method is unsupported.")

    async def _record_failure(
        self,
        transaction_id: UUID,
        *,
        error_code: str,
        error_message: str,
        actor_service: str,
    ) -> None:
        async with self._session.begin():
            transaction = await self._required(transaction_id, for_update=True)
            if transaction.status is BlockchainTransactionStatus.CONFIRMED:
                return
            transaction.status = BlockchainTransactionStatus.FAILED
            transaction.error_code = error_code
            transaction.error_message = error_message[:2_000]
            self._audit(
                "blockchain.transaction.failed",
                transaction.id,
                actor_service=actor_service,
                status=BlockchainTransactionStatus.FAILED,
                error_code=error_code,
            )
            if transaction.method == "updateCertificate":
                version = await self._session.scalar(
                    select(CertificateVersion).where(
                        CertificateVersion.blockchain_transaction_id == transaction.id
                    )
                )
                if (
                    version is not None
                    and version.status is CertificateVersionStatus.ANCHOR_PENDING
                ):
                    version.status = CertificateVersionStatus.FAILED
            if transaction.document_evidence_id is not None:
                evidence = await self._session.get(
                    DocumentBlockchainEvidence,
                    transaction.document_evidence_id,
                )
                if evidence is not None:
                    evidence.status = DocumentEvidenceStatus.FAILED

    async def _promote_confirmed_version(
        self,
        transaction: BlockchainTransaction,
    ) -> UUID:
        version = await self._session.scalar(
            select(CertificateVersion)
            .where(CertificateVersion.blockchain_transaction_id == transaction.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if version is None:
            raise BlockchainConflictError(
                "Confirmed certificate version context is unavailable."
            )
        if version.status is CertificateVersionStatus.ACTIVE:
            return version.id
        if version.status is not CertificateVersionStatus.ANCHOR_PENDING:
            raise BlockchainConflictError(
                "Confirmed certificate version is not awaiting promotion."
            )
        if version.predecessor_version_id is None:
            raise BlockchainConflictError(
                "Certificate version predecessor is unavailable."
            )
        predecessor = await self._session.scalar(
            select(CertificateVersion)
            .where(CertificateVersion.id == version.predecessor_version_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        certificate = await self._session.scalar(
            select(Certificate)
            .where(Certificate.id == version.certificate_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            predecessor is None
            or predecessor.status is not CertificateVersionStatus.ACTIVE
            or certificate is None
            or certificate.current_version_no != predecessor.version_no
            or version.version_no != predecessor.version_no + 1
        ):
            raise BlockchainConflictError(
                "Certificate version lineage changed before confirmation."
            )
        predecessor.status = CertificateVersionStatus.SUPERSEDED
        await self._session.flush()
        version.status = CertificateVersionStatus.ACTIVE
        certificate.current_version_no = version.version_no
        certificate.pdf_media_id = None
        return version.id

    async def _confirm_certificate_revocation(
        self,
        transaction: BlockchainTransaction,
    ) -> None:
        if transaction.certificate_id is None:
            raise BlockchainConflictError("Revoked certificate context is unavailable.")
        certificate = await self._session.scalar(
            select(Certificate)
            .where(Certificate.id == transaction.certificate_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if certificate is None:
            raise BlockchainConflictError("Revoked certificate context is unavailable.")
        version = await self._session.scalar(
            select(CertificateVersion)
            .where(
                CertificateVersion.certificate_id == certificate.id,
                CertificateVersion.version_no == certificate.current_version_no,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if version is None:
            raise BlockchainConflictError(
                "Revoked certificate version context is unavailable."
            )
        revoked_at = self._clock()
        certificate.status = CertificateStatus.REVOKED
        certificate.revoked_at = revoked_at
        version.status = CertificateVersionStatus.REVOKED
        version.revoked_at = revoked_at

    async def _record_reconciliation_mismatch(
        self,
        transaction_id: UUID,
        error_message: str,
    ) -> None:
        mismatch_recorded = False
        async with self._session.begin():
            transaction = await self._required(transaction_id, for_update=True)
            mismatch_recorded = transaction.error_code != "CHAIN_STATE_MISMATCH"
            transaction.error_code = "CHAIN_STATE_MISMATCH"
            transaction.error_message = error_message[:2_000]
            if transaction.document_evidence_id is not None:
                evidence = await self._session.get(
                    DocumentBlockchainEvidence,
                    transaction.document_evidence_id,
                )
                if evidence is not None:
                    evidence.status = DocumentEvidenceStatus.FAILED
            if mismatch_recorded:
                self._audit(
                    "blockchain.reconciliation.mismatch",
                    transaction.id,
                    actor_service="blockchain-confirmation-worker",
                    error_code="CHAIN_STATE_MISMATCH",
                )
        if mismatch_recorded:
            logger.error(
                "blockchain.reconciliation.mismatch",
                extra={"transaction_id": str(transaction_id)},
            )

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

    async def _document_evidence_transaction(
        self,
        document_evidence_id: UUID,
    ) -> BlockchainTransaction:
        transaction = await self._session.scalar(
            select(BlockchainTransaction).where(
                BlockchainTransaction.document_evidence_id == document_evidence_id
            )
        )
        if transaction is None:
            raise BlockchainConflictError(
                "Document evidence transaction context is unavailable."
            )
        return transaction

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="blockchain.manage",
                compatible_roles=BLOCKCHAIN_ADMIN_ROLES,
            ),
            BlockchainForbiddenError,
        )

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

    async def _document_evidence_view(
        self,
        evidence: DocumentBlockchainEvidence,
        transaction: BlockchainTransaction,
    ) -> DocumentEvidenceView:
        previous_evidence_key: str | None = None
        if evidence.predecessor_evidence_id is not None:
            predecessor = await self._session.get(
                DocumentBlockchainEvidence,
                evidence.predecessor_evidence_id,
            )
            if predecessor is None:
                raise BlockchainConflictError(
                    "Document evidence predecessor context is unavailable."
                )
            previous_evidence_key = predecessor.evidence_key
        return DocumentEvidenceView(
            id=evidence.id,
            document_hash_claim_id=evidence.document_hash_claim_id,
            dossier_id=evidence.dossier_id,
            dossier_version_id=evidence.dossier_version_id,
            evidence_key=evidence.evidence_key,
            commitment=evidence.commitment,
            version_no=evidence.version_no,
            previous_evidence_key=previous_evidence_key,
            recorded_at=evidence.recorded_at,
            status=evidence.status,
            transaction_id=transaction.id,
            network=transaction.network,
            tx_hash=transaction.tx_hash,
            confirmations=transaction.confirmations,
            error_code=transaction.error_code,
            created_at=evidence.created_at,
            updated_at=evidence.updated_at,
        )

    def _audit(
        self,
        action: str,
        transaction_id: UUID | None,
        *,
        actor_user_id: UUID | None = None,
        actor_service: str | None = None,
        status: BlockchainTransactionStatus | None = None,
        confirmations: int | None = None,
        error_code: str | None = None,
    ) -> None:
        after: dict[str, object] = {}
        if status is not None:
            after["status"] = status.value
        if confirmations is not None:
            after["confirmations"] = confirmations
        if error_code is not None:
            after["error_code"] = error_code
        self._audit_service.record(
            actor_user_id=actor_user_id,
            actor_service=actor_service,
            action=action,
            resource_type="blockchain_transaction",
            resource_id=(str(transaction_id) if transaction_id is not None else "all"),
            after=after or None,
        )
