"""Database-only administration views for blockchain history."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import (
    BlockchainConflictError,
    BlockchainForbiddenError,
)
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    DocumentBlockchainEvidence,
    DocumentEvidenceStatus,
)
from app.modules.blockchain.repository import BlockchainTransactionRepository


@dataclass(frozen=True, slots=True)
class DocumentEvidenceHistoryView:
    id: UUID
    document_hash_claim_id: UUID
    dossier_id: UUID
    dossier_version_id: UUID
    evidence_key: str
    commitment: str
    version_no: int
    previous_evidence_key: str | None
    recorded_at: datetime
    status: DocumentEvidenceStatus
    transaction_id: UUID
    network: str
    tx_hash: str | None
    confirmations: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class BlockchainAdminReadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = BlockchainTransactionRepository(session)

    async def list_transactions(
        self,
        principal: AuthPrincipal,
        *,
        status: BlockchainTransactionStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[BlockchainTransaction, ...], int]:
        self._require_admin(principal)
        async with self._session.begin():
            return await self._repository.list(
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    async def list_document_evidences(
        self,
        principal: AuthPrincipal,
        *,
        status: DocumentEvidenceStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[DocumentEvidenceHistoryView, ...], int]:
        self._require_admin(principal)
        async with self._session.begin():
            rows, total = await self._repository.list_document_evidences(
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            views = tuple(
                [
                    await self._evidence_view(evidence, transaction)
                    for evidence, transaction in rows
                ]
            )
            return views, total

    async def _evidence_view(
        self,
        evidence: DocumentBlockchainEvidence,
        transaction: BlockchainTransaction,
    ) -> DocumentEvidenceHistoryView:
        previous_evidence_key: str | None = None
        if evidence.predecessor_evidence_id is not None:
            predecessor = await self._session.get(
                DocumentBlockchainEvidence, evidence.predecessor_evidence_id
            )
            if predecessor is None:
                raise BlockchainConflictError(
                    "Document evidence predecessor context is unavailable."
                )
            previous_evidence_key = predecessor.evidence_key
        return DocumentEvidenceHistoryView(
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

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="blockchain.manage",
                compatible_roles=frozenset({"SUPER_ADMIN"}),
            ),
            BlockchainForbiddenError,
        )
