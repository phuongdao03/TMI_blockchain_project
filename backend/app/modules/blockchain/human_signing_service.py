"""Server-side authorization for transactions broadcast by a human wallet."""

import hashlib
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
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
)
from app.modules.blockchain.gateway import BlockchainGateway
from app.modules.blockchain.human_signing import (
    build_wallet_challenge_message,
    normalize_wallet_address,
    recover_wallet_address,
)
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionIntent,
    BlockchainTransactionIntentStatus,
    BlockchainTransactionStatus,
    BlockchainWalletChallenge,
    BlockchainWalletLink,
    BlockchainWalletLinkStatus,
    Certificate,
    CertificateVersion,
    DocumentBlockchainEvidence,
    DocumentEvidenceStatus,
)
from app.modules.dossiers.models import (
    DocumentHashAnchor,
    DocumentHashClaim,
    Dossier,
    DossierStatus,
    DossierVersion,
)

EnqueueSignal = Callable[[], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class WalletChallengeView:
    id: UUID
    message: str
    nonce: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class WalletLinkView:
    id: UUID
    wallet_address: str
    chain_id: int
    status: BlockchainWalletLinkStatus
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class SigningQueueItemView:
    transaction_id: UUID
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    dossier_version_no: int
    certificate_number: str | None
    proof_hash: str
    status: BlockchainTransactionStatus
    tx_hash: str | None
    error_code: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SigningContextView:
    transaction_id: UUID
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    dossier_version_no: int
    certificate_number: str | None
    method: str
    proof_hash: str
    network: str
    chain_id: int
    contract_address: str
    status: BlockchainTransactionStatus


@dataclass(frozen=True, slots=True)
class SigningIntentView:
    id: UUID
    transaction_id: UUID
    transaction_request: dict[str, str]
    expires_at: datetime
    estimated_gas: int
    gas_price_wei: int
    wallet_balance_wei: int


@dataclass(frozen=True, slots=True)
class SigningStatusView:
    transaction_id: UUID
    status: BlockchainTransactionStatus
    tx_hash: str | None
    confirmations: int
    error_code: str | None
    error_message: str | None
    confirmed_at: datetime | None


class HumanSigningService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: BlockchainGateway,
        network: str,
        chain_id: int,
        contract_address: str,
        challenge_ttl_seconds: int,
        intent_ttl_seconds: int,
        signing_enabled: bool,
        enqueue_reconcile: EnqueueSignal | None = None,
        clock: Callable[[], datetime] | None = None,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._session = session
        self._gateway = gateway
        self._network = network
        self._chain_id = chain_id
        self._contract_address = contract_address.lower()
        self._challenge_ttl = timedelta(seconds=challenge_ttl_seconds)
        self._intent_ttl = timedelta(seconds=intent_ttl_seconds)
        self._signing_enabled = signing_enabled
        self._enqueue_reconcile = enqueue_reconcile
        self._clock = clock or (lambda: datetime.now(UTC))
        self._nonce_factory = nonce_factory or (lambda: secrets.token_urlsafe(32))
        self._audit = AuditService(session)

    async def create_wallet_challenge(
        self,
        principal: AuthPrincipal,
        *,
        wallet_address: str,
        chain_id: int,
    ) -> WalletChallengeView:
        self._require_signer(principal)
        address = self._require_address(wallet_address)
        if chain_id != self._chain_id:
            raise BlockchainConflictError("Wallet chain does not match THV network.")
        nonce = self._nonce_factory()
        now = self._clock()
        expires_at = now + self._challenge_ttl
        challenge = BlockchainWalletChallenge(
            id=uuid4(),
            user_id=principal.user_id,
            wallet_address=address,
            chain_id=chain_id,
            nonce_hash=hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
        )
        async with self._session.begin():
            self._session.add(challenge)
            self._audit.record(
                actor_user_id=principal.user_id,
                action="blockchain.wallet.challenge_issued",
                resource_type="blockchain_wallet_challenge",
                resource_id=str(challenge.id),
                after={"wallet": address, "chain_id": chain_id},
            )
        return WalletChallengeView(
            id=challenge.id,
            message=build_wallet_challenge_message(
                user_id=principal.user_id,
                wallet_address=address,
                chain_id=chain_id,
                nonce=nonce,
                expires_at=expires_at,
            ),
            nonce=nonce,
            expires_at=expires_at,
        )

    async def verify_wallet_link(
        self,
        principal: AuthPrincipal,
        *,
        challenge_id: UUID,
        nonce: str,
        signature: str,
    ) -> WalletLinkView:
        self._require_signer(principal)
        now = self._clock()
        async with self._session.begin():
            challenge = await self._session.scalar(
                select(BlockchainWalletChallenge)
                .where(
                    BlockchainWalletChallenge.id == challenge_id,
                    BlockchainWalletChallenge.user_id == principal.user_id,
                )
                .with_for_update()
            )
            if challenge is None:
                raise BlockchainNotFoundError()
            supplied_hash = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
            if (
                challenge.consumed_at is not None
                or self._as_utc(challenge.expires_at) <= now
                or not secrets.compare_digest(challenge.nonce_hash, supplied_hash)
            ):
                raise BlockchainConflictError(
                    "Wallet verification challenge has expired."
                )
            message = build_wallet_challenge_message(
                user_id=principal.user_id,
                wallet_address=challenge.wallet_address,
                chain_id=int(challenge.chain_id),
                nonce=nonce,
                expires_at=self._as_utc(challenge.expires_at),
            )
            recovered = recover_wallet_address(message, signature)
            if recovered != challenge.wallet_address:
                raise BlockchainConflictError(
                    "Wallet signature does not match challenge."
                )
            challenge.consumed_at = now
            current = await self._active_wallet_link(for_update=True)
            if current is not None:
                if (
                    current.user_id == principal.user_id
                    and current.wallet_address == recovered
                ):
                    return self._wallet_view(current)
                raise BlockchainConflictError(
                    "An active blockchain signer wallet is already configured."
                )
            existing = await self._session.scalar(
                select(BlockchainWalletLink)
                .where(BlockchainWalletLink.wallet_address == recovered)
                .with_for_update()
            )
            if existing is not None:
                raise BlockchainConflictError(
                    "This wallet cannot be linked to this user."
                )
            link = BlockchainWalletLink(
                id=uuid4(),
                user_id=principal.user_id,
                wallet_address=recovered,
                chain_id=challenge.chain_id,
                status=BlockchainWalletLinkStatus.ACTIVE,
                is_active=True,
                verified_at=now,
            )
            self._session.add(link)
            self._audit.record(
                actor_user_id=principal.user_id,
                action="blockchain.wallet.linked",
                resource_type="blockchain_wallet_link",
                resource_id=str(link.id),
                after={"wallet": recovered, "chain_id": int(link.chain_id)},
            )
            await self._session.flush()
            return self._wallet_view(link)

    async def current_wallet(self, principal: AuthPrincipal) -> WalletLinkView | None:
        self._require_signer(principal)
        async with self._session.begin():
            link = await self._session.scalar(
                select(BlockchainWalletLink).where(
                    BlockchainWalletLink.user_id == principal.user_id,
                    BlockchainWalletLink.is_active.is_(True),
                )
            )
            return self._wallet_view(link) if link is not None else None

    async def revoke_current_wallet(self, principal: AuthPrincipal) -> WalletLinkView:
        """Deactivate the sole signer wallet before a controlled rotation."""
        self._require_signer(principal)
        now = self._clock()
        async with self._session.begin():
            link = await self._active_wallet_link(for_update=True)
            if link is None or link.user_id != principal.user_id:
                raise BlockchainForbiddenError()
            link.status = BlockchainWalletLinkStatus.REVOKED
            link.is_active = False
            link.revoked_at = now
            intents = await self._session.scalars(
                select(BlockchainTransactionIntent)
                .where(
                    BlockchainTransactionIntent.signer_user_id == principal.user_id,
                    BlockchainTransactionIntent.status
                    == BlockchainTransactionIntentStatus.PREPARED,
                )
                .with_for_update()
            )
            for intent in intents:
                intent.status = BlockchainTransactionIntentStatus.CANCELLED
                transaction = await self._required_transaction(
                    intent.transaction_id,
                    for_update=True,
                )
                if (
                    transaction.status is BlockchainTransactionStatus.SIGNING
                    and transaction.tx_hash is None
                ):
                    transaction.status = BlockchainTransactionStatus.CREATED
            self._audit.record(
                actor_user_id=principal.user_id,
                action="blockchain.wallet.revoked",
                resource_type="blockchain_wallet_link",
                resource_id=str(link.id),
                before={"wallet": link.wallet_address},
                after={"reason": "signer_rotation"},
            )
            await self._session.flush()
            return self._wallet_view(link)

    async def list_signing_queue(
        self,
        principal: AuthPrincipal,
    ) -> tuple[SigningQueueItemView, ...]:
        self._require_signer(principal)
        await self._require_owned_active_wallet(principal)
        async with self._session.begin():
            rows = await self._session.execute(
                select(BlockchainTransaction, Dossier, DossierVersion, Certificate)
                .join(Dossier, Dossier.id == BlockchainTransaction.dossier_id)
                .join(
                    DossierVersion,
                    DossierVersion.id == BlockchainTransaction.dossier_version_id,
                )
                .outerjoin(
                    Certificate, Certificate.id == BlockchainTransaction.certificate_id
                )
                .where(
                    BlockchainTransaction.status.in_(
                        (
                            BlockchainTransactionStatus.CREATED,
                            BlockchainTransactionStatus.SIGNING,
                            BlockchainTransactionStatus.BROADCAST,
                            BlockchainTransactionStatus.FAILED,
                        )
                    )
                )
                .order_by(BlockchainTransaction.created_at)
            )
            return tuple(
                SigningQueueItemView(
                    transaction_id=transaction.id,
                    dossier_id=dossier.id,
                    dossier_code=dossier.code,
                    dossier_title=dossier.title,
                    dossier_version_no=version.version_no,
                    certificate_number=(
                        certificate.certificate_number if certificate else None
                    ),
                    proof_hash=transaction.payload_hash,
                    status=transaction.status,
                    tx_hash=transaction.tx_hash,
                    error_code=transaction.error_code,
                    created_at=transaction.created_at,
                )
                for transaction, dossier, version, certificate in rows.tuples()
            )

    async def signing_context(
        self,
        principal: AuthPrincipal,
        transaction_id: UUID,
    ) -> SigningContextView:
        self._require_signer(principal)
        await self._require_owned_active_wallet(principal)
        async with self._session.begin():
            transaction, dossier, version, certificate = await self._transaction_row(
                transaction_id
            )
            return SigningContextView(
                transaction_id=transaction.id,
                dossier_id=dossier.id,
                dossier_code=dossier.code,
                dossier_title=dossier.title,
                dossier_version_no=version.version_no,
                certificate_number=(
                    certificate.certificate_number if certificate else None
                ),
                method=transaction.method,
                proof_hash=transaction.payload_hash,
                network=transaction.network,
                chain_id=int(transaction.chain_id),
                contract_address=transaction.contract_address,
                status=transaction.status,
            )

    async def prepare_intent(
        self,
        principal: AuthPrincipal,
        *,
        transaction_id: UUID,
        connected_wallet: str,
    ) -> SigningIntentView:
        self._require_signer(principal)
        await self._require_owned_active_wallet(principal)
        self._require_enabled()
        wallet = await self._require_active_wallet(principal, connected_wallet)
        if not await self._gateway.has_issuer_role(wallet.wallet_address):
            raise BlockchainForbiddenError()
        async with self._session.begin():
            transaction = await self._required_transaction(transaction_id)
            payload = await self._payload_for_transaction(transaction)
            await self._validate_transaction_for_intent(transaction, payload)
        estimated_gas = await self._gateway.estimate_gas(
            signer=wallet.wallet_address,
            payload=payload,
        )
        gas_price = await self._gateway.gas_price()
        balance = await self._gateway.balance(wallet.wallet_address)
        now = self._clock()
        async with self._session.begin():
            transaction = await self._required_transaction(
                transaction_id, for_update=True
            )
            payload = await self._payload_for_transaction(transaction)
            await self._validate_transaction_for_intent(transaction, payload)
            current = await self._active_intent(transaction.id, for_update=True)
            if current is not None and self._as_utc(current.expires_at) <= now:
                current.status = BlockchainTransactionIntentStatus.EXPIRED
                current = None
            if current is not None:
                if current.signer_user_id != principal.user_id:
                    raise BlockchainConflictError(
                        "A signing request is already active."
                    )
                return self._intent_view(
                    current,
                    payload=payload,
                    estimated_gas=estimated_gas,
                    gas_price=gas_price,
                    balance=balance,
                )
            intent = BlockchainTransactionIntent(
                id=uuid4(),
                transaction_id=transaction.id,
                dossier_id=transaction.dossier_id,
                dossier_version_id=transaction.dossier_version_id,
                signer_user_id=principal.user_id,
                expected_wallet_address=wallet.wallet_address,
                network=self._network,
                chain_id=self._chain_id,
                contract_address=self._contract_address,
                proof_hash=transaction.payload_hash,
                encoded_call_hash=hashlib.sha256(payload).hexdigest(),
                status=BlockchainTransactionIntentStatus.PREPARED,
                expires_at=now + self._intent_ttl,
            )
            self._session.add(intent)
            transaction.status = BlockchainTransactionStatus.SIGNING
            self._audit.record(
                actor_user_id=principal.user_id,
                action="blockchain.signature.requested",
                resource_type="blockchain_transaction",
                resource_id=str(transaction.id),
                after={"wallet": wallet.wallet_address, "intent_id": str(intent.id)},
            )
            await self._session.flush()
            return self._intent_view(
                intent,
                payload=payload,
                estimated_gas=estimated_gas,
                gas_price=gas_price,
                balance=balance,
            )

    async def submit_transaction(
        self,
        principal: AuthPrincipal,
        *,
        transaction_id: UUID,
        intent_id: UUID,
        transaction_hash: str,
        connected_wallet: str,
    ) -> SigningStatusView:
        self._require_signer(principal)
        self._require_enabled()
        wallet = await self._require_active_wallet(principal, connected_wallet)
        async with self._session.begin():
            intent = await self._required_intent(intent_id)
            if intent.transaction_id != transaction_id:
                raise BlockchainConflictError("Transaction intent does not match.")
            expected_hash = intent.encoded_call_hash
            expected_wallet = intent.expected_wallet_address
            expected_contract = intent.contract_address
            expected_chain = int(intent.chain_id)
        chain_transaction = await self._gateway.transaction(transaction_hash)
        if chain_transaction is None:
            raise BlockchainConflictError("Blockchain transaction was not found.")
        if (
            chain_transaction.sender != expected_wallet
            or chain_transaction.sender != wallet.wallet_address
            or chain_transaction.recipient.lower() != expected_contract.lower()
            or chain_transaction.chain_id != expected_chain
            or chain_transaction.value != 0
            or hashlib.sha256(chain_transaction.data).hexdigest() != expected_hash
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
                intent.transaction_id != transaction.id
                or intent.signer_user_id != principal.user_id
                or intent.expected_wallet_address != wallet.wallet_address
                or intent.status is not BlockchainTransactionIntentStatus.PREPARED
                or self._as_utc(intent.expires_at) <= now
            ):
                if intent.status is BlockchainTransactionIntentStatus.PREPARED:
                    intent.status = BlockchainTransactionIntentStatus.EXPIRED
                raise BlockchainConflictError(
                    "Blockchain signing intent is no longer valid."
                )
            if (
                transaction.tx_hash is not None
                and transaction.tx_hash.lower() != transaction_hash.lower()
            ):
                raise BlockchainConflictError(
                    "A different transaction is already recorded."
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
            if transaction.document_evidence_id is not None:
                evidence = await self._session.get(
                    DocumentBlockchainEvidence,
                    transaction.document_evidence_id,
                )
                if evidence is None:
                    raise BlockchainConflictError(
                        "Document evidence context is unavailable."
                    )
                evidence.status = DocumentEvidenceStatus.BROADCAST
            intent.status = BlockchainTransactionIntentStatus.SUBMITTED
            intent.submitted_at = now
            self._audit.record(
                actor_user_id=principal.user_id,
                action="blockchain.transaction.submitted",
                resource_type="blockchain_transaction",
                resource_id=str(transaction.id),
                after={"wallet": wallet.wallet_address, "tx_hash": transaction.tx_hash},
            )
            view = self._status_view(transaction)
        if self._enqueue_reconcile is not None:
            result = self._enqueue_reconcile()
            if result is not None:
                await result
        return view

    async def transaction_status(
        self,
        principal: AuthPrincipal,
        transaction_id: UUID,
    ) -> SigningStatusView:
        self._require_signer(principal)
        await self._require_owned_active_wallet(principal)
        async with self._session.begin():
            return self._status_view(await self._required_transaction(transaction_id))

    async def _require_active_wallet(
        self,
        principal: AuthPrincipal,
        connected_wallet: str,
    ) -> BlockchainWalletLink:
        address = self._require_address(connected_wallet)
        async with self._session.begin():
            link = await self._active_wallet_link()
            if (
                link is None
                or link.user_id != principal.user_id
                or link.wallet_address != address
                or int(link.chain_id) != self._chain_id
            ):
                raise BlockchainForbiddenError()
            return link

    async def _require_owned_active_wallet(
        self,
        principal: AuthPrincipal,
    ) -> BlockchainWalletLink:
        async with self._session.begin():
            link = await self._active_wallet_link()
            if link is None or link.user_id != principal.user_id:
                raise BlockchainForbiddenError()
            return link

    async def _active_wallet_link(
        self,
        *,
        for_update: bool = False,
    ) -> BlockchainWalletLink | None:
        statement = select(BlockchainWalletLink).where(
            BlockchainWalletLink.is_active.is_(True),
            BlockchainWalletLink.status == BlockchainWalletLinkStatus.ACTIVE,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(BlockchainWalletLink | None, await self._session.scalar(statement))

    async def _active_intent(
        self,
        transaction_id: UUID,
        *,
        for_update: bool = False,
    ) -> BlockchainTransactionIntent | None:
        statement = select(BlockchainTransactionIntent).where(
            BlockchainTransactionIntent.transaction_id == transaction_id,
            BlockchainTransactionIntent.status
            == BlockchainTransactionIntentStatus.PREPARED,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(
            BlockchainTransactionIntent | None,
            await self._session.scalar(statement),
        )

    async def _required_transaction(
        self,
        transaction_id: UUID,
        *,
        for_update: bool = False,
    ) -> BlockchainTransaction:
        statement = select(BlockchainTransaction).where(
            BlockchainTransaction.id == transaction_id
        )
        if for_update:
            statement = statement.with_for_update()
        transaction = await self._session.scalar(statement)
        if transaction is None:
            raise BlockchainNotFoundError()
        return transaction

    async def _required_intent(
        self,
        intent_id: UUID,
        *,
        for_update: bool = False,
    ) -> BlockchainTransactionIntent:
        statement = select(BlockchainTransactionIntent).where(
            BlockchainTransactionIntent.id == intent_id
        )
        if for_update:
            statement = statement.with_for_update()
        intent = await self._session.scalar(statement)
        if intent is None:
            raise BlockchainNotFoundError()
        return intent

    async def _transaction_row(
        self,
        transaction_id: UUID,
    ) -> tuple[BlockchainTransaction, Dossier, DossierVersion, Certificate | None]:
        row = await self._session.execute(
            select(BlockchainTransaction, Dossier, DossierVersion, Certificate)
            .join(Dossier, Dossier.id == BlockchainTransaction.dossier_id)
            .join(
                DossierVersion,
                DossierVersion.id == BlockchainTransaction.dossier_version_id,
            )
            .outerjoin(
                Certificate, Certificate.id == BlockchainTransaction.certificate_id
            )
            .where(BlockchainTransaction.id == transaction_id)
        )
        result = row.tuples().one_or_none()
        if result is None:
            raise BlockchainNotFoundError()
        return result

    async def _payload_for_transaction(
        self, transaction: BlockchainTransaction
    ) -> bytes:
        if transaction.method == "anchorDocumentEvidence":
            return await self._document_evidence_payload(transaction)
        if transaction.certificate_id is None:
            raise BlockchainConflictError(
                "Transaction certificate context is unavailable."
            )
        certificate = await self._session.get(Certificate, transaction.certificate_id)
        version = await self._session.scalar(
            select(CertificateVersion).where(
                CertificateVersion.certificate_id == transaction.certificate_id,
                CertificateVersion.dossier_version_id == transaction.dossier_version_id,
            )
        )
        dossier_version = await self._session.get(
            DossierVersion, transaction.dossier_version_id
        )
        if certificate is None or version is None or dossier_version is None:
            raise BlockchainConflictError("Frozen certificate proof is unavailable.")
        certificate_key = hashlib.sha256(
            certificate.certificate_number.encode()
        ).digest()
        dossier_hash = bytes.fromhex(dossier_version.canonical_hash)
        metadata_hash = bytes.fromhex(version.metadata_hash)
        if transaction.method == "issueCertificate":
            return self._gateway.encode_issue_certificate(
                certificate_id=certificate_key,
                dossier_hash=dossier_hash,
                metadata_hash=metadata_hash,
                issued_at=int(self._as_utc(certificate.issued_at).timestamp()),
                expires_at=(
                    int(self._as_utc(certificate.expires_at).timestamp())
                    if certificate.expires_at
                    else 0
                ),
            )
        if transaction.method == "updateCertificate":
            return self._gateway.encode_update_certificate(
                certificate_id=certificate_key,
                dossier_hash=dossier_hash,
                metadata_hash=metadata_hash,
                version=version.version_no,
            )
        if (
            transaction.method == "revokeCertificate"
            and certificate.revocation_reason_hash
        ):
            return self._gateway.encode_revoke_certificate(
                certificate_id=certificate_key,
                reason_hash=bytes.fromhex(certificate.revocation_reason_hash),
            )
        raise BlockchainConflictError(
            "Transaction method is not supported for signing."
        )

    async def _document_evidence_payload(
        self,
        transaction: BlockchainTransaction,
    ) -> bytes:
        if transaction.document_evidence_id is None:
            raise BlockchainConflictError("Document evidence context is unavailable.")
        evidence = await self._session.get(
            DocumentBlockchainEvidence,
            transaction.document_evidence_id,
        )
        if evidence is None:
            raise BlockchainConflictError("Document evidence context is unavailable.")
        claim = await self._session.get(
            DocumentHashClaim, evidence.document_hash_claim_id
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
        recorded_at = self._as_utc(evidence.recorded_at)
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

    async def _validate_transaction_for_intent(
        self,
        transaction: BlockchainTransaction,
        payload: bytes,
    ) -> None:
        if (
            transaction.network != self._network
            or int(transaction.chain_id) != self._chain_id
        ):
            raise BlockchainConflictError(
                "Transaction network does not match configuration."
            )
        if transaction.contract_address.lower() != self._contract_address:
            raise BlockchainConflictError("Transaction contract is not allowed.")
        if transaction.method == "issueCertificate":
            dossier = await self._session.get(Dossier, transaction.dossier_id)
            if dossier is None or dossier.status is not DossierStatus.ANCHOR_PENDING:
                raise BlockchainConflictError(
                    "Dossier is not waiting for a blockchain signature."
                )
        if (
            transaction.status
            not in {
                BlockchainTransactionStatus.CREATED,
                BlockchainTransactionStatus.SIGNING,
            }
            or transaction.tx_hash is not None
        ):
            raise BlockchainConflictError("Transaction is not waiting for a signature.")
        if hashlib.sha256(payload).hexdigest() != transaction.payload_hash:
            raise BlockchainConflictError("Frozen blockchain proof has changed.")

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
    def _as_utc(value: datetime) -> datetime:
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )

    @staticmethod
    def _wallet_view(link: BlockchainWalletLink) -> WalletLinkView:
        return WalletLinkView(
            id=link.id,
            wallet_address=link.wallet_address,
            chain_id=int(link.chain_id),
            status=link.status,
            verified_at=link.verified_at,
        )

    @staticmethod
    def _status_view(transaction: BlockchainTransaction) -> SigningStatusView:
        return SigningStatusView(
            transaction_id=transaction.id,
            status=transaction.status,
            tx_hash=transaction.tx_hash,
            confirmations=transaction.confirmations,
            error_code=transaction.error_code,
            error_message=transaction.error_message,
            confirmed_at=transaction.confirmed_at,
        )

    def _intent_view(
        self,
        intent: BlockchainTransactionIntent,
        *,
        payload: bytes,
        estimated_gas: int,
        gas_price: int,
        balance: int,
    ) -> SigningIntentView:
        return SigningIntentView(
            id=intent.id,
            transaction_id=intent.transaction_id,
            transaction_request={
                "from": intent.expected_wallet_address,
                "to": intent.contract_address,
                "data": "0x" + payload.hex(),
                "value": "0x0",
                "gas": hex(estimated_gas),
                "gasPrice": hex(gas_price),
                "chainId": hex(int(intent.chain_id)),
            },
            expires_at=intent.expires_at,
            estimated_gas=estimated_gas,
            gas_price_wei=gas_price,
            wallet_balance_wei=balance,
        )
