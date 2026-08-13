import hashlib
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.document_evidence import build_document_evidence_commitment
from app.modules.blockchain.gateway import BlockchainGatewayError
from app.modules.blockchain.models import (
    DocumentBlockchainEvidence,
    DocumentEvidenceStatus,
)
from app.modules.dossiers.models import DocumentHashAnchor, DocumentHashClaim
from app.modules.media.models import MediaAsset, MediaStatus


class DocumentVerificationStatus(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    CHAIN_UNAVAILABLE = "CHAIN_UNAVAILABLE"
    NOT_FOUND = "NOT_FOUND"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"


class DocumentVerificationTooLargeError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_VERIFICATION_TOO_LARGE",
            message="The document exceeds the verification size limit.",
            status_code=413,
        )


@dataclass(frozen=True, slots=True)
class DocumentVerificationView:
    status: DocumentVerificationStatus
    checked_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentProofReference:
    media_asset_id: UUID
    owner_user_id: UUID
    expected_sha256: str | None
    evidence_key: str | None
    commitment: str | None
    evidence_status: DocumentEvidenceStatus | None
    document_hash_claim_id: UUID | None = None
    version_no: int | None = None
    submitter_reference: str | None = None
    previous_evidence_key: str | None = None
    recorded_at: datetime | None = None


class DocumentProofRepository(Protocol):
    async def find_by_media_id(
        self,
        media_id: UUID,
    ) -> DocumentProofReference | None: ...


class DocumentDeliveryAccessPolicy(Protocol):
    async def can_deliver(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> bool: ...


class DocumentEvidenceVerifier(Protocol):
    async def verify_document_evidence(
        self,
        *,
        evidence_key: bytes,
        commitment: bytes,
    ) -> bool: ...


class SqlDocumentProofRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_media_id(
        self,
        media_id: UUID,
    ) -> DocumentProofReference | None:
        proof = (
            await self._session.execute(
                select(
                    MediaAsset.id.label("media_asset_id"),
                    MediaAsset.owner_user_id,
                    MediaAsset.sha256.label("asset_sha256"),
                    DocumentHashClaim.id.label("document_hash_claim_id"),
                    DocumentHashAnchor.sha256.label("claim_sha256"),
                    DocumentBlockchainEvidence.evidence_key,
                    DocumentBlockchainEvidence.commitment,
                    DocumentBlockchainEvidence.status,
                    DocumentBlockchainEvidence.version_no,
                    DocumentBlockchainEvidence.submitter_reference,
                    DocumentBlockchainEvidence.recorded_at,
                    DocumentBlockchainEvidence.predecessor_evidence_id,
                )
                .select_from(MediaAsset)
                .outerjoin(
                    DocumentHashClaim,
                    DocumentHashClaim.media_asset_id == MediaAsset.id,
                )
                .outerjoin(
                    DocumentHashAnchor,
                    DocumentHashAnchor.id == DocumentHashClaim.anchor_id,
                )
                .outerjoin(
                    DocumentBlockchainEvidence,
                    DocumentBlockchainEvidence.document_hash_claim_id
                    == DocumentHashClaim.id,
                )
                .where(
                    MediaAsset.id == media_id,
                    MediaAsset.status == MediaStatus.ACTIVE,
                )
            )
        ).one_or_none()
        if proof is None:
            return None
        return DocumentProofReference(
            media_asset_id=proof.media_asset_id,
            owner_user_id=proof.owner_user_id,
            expected_sha256=(
                str(proof.claim_sha256)
                if proof.claim_sha256 is not None
                else proof.asset_sha256
            ),
            evidence_key=(
                str(proof.evidence_key) if proof.evidence_key is not None else None
            ),
            commitment=(
                str(proof.commitment) if proof.commitment is not None else None
            ),
            evidence_status=proof.status,
            document_hash_claim_id=proof.document_hash_claim_id,
            version_no=proof.version_no,
            submitter_reference=proof.submitter_reference,
            previous_evidence_key=await self._previous_evidence_key(
                proof.predecessor_evidence_id,
            ),
            recorded_at=proof.recorded_at,
        )

    async def _previous_evidence_key(
        self,
        predecessor_evidence_id: UUID | None,
    ) -> str | None:
        if predecessor_evidence_id is None:
            return None
        predecessor = await self._session.scalar(
            select(DocumentBlockchainEvidence.evidence_key).where(
                DocumentBlockchainEvidence.id == predecessor_evidence_id
            )
        )
        return str(predecessor) if predecessor is not None else None


async def _bounded_sha256(
    chunks: AsyncIterator[bytes],
    *,
    max_bytes: int,
) -> str:
    digest = hashlib.sha256()
    received = 0
    async for chunk in chunks:
        received += len(chunk)
        if received > max_bytes:
            raise DocumentVerificationTooLargeError()
        digest.update(chunk)
    if received == 0:
        return ""
    return digest.hexdigest()


async def verify_public_document(
    *,
    expected_sha256: str | None,
    certificate_is_confirmed: bool,
    chunks: AsyncIterator[bytes],
    max_bytes: int,
    clock: Callable[[], datetime] | None = None,
) -> DocumentVerificationView:
    checked_at = (clock or (lambda: datetime.now(UTC)))()
    if expected_sha256 is None:
        return DocumentVerificationView(
            status=DocumentVerificationStatus.NOT_FOUND,
            checked_at=checked_at,
        )
    if not certificate_is_confirmed:
        return DocumentVerificationView(
            status=DocumentVerificationStatus.PENDING_CONFIRMATION,
            checked_at=checked_at,
        )
    candidate_sha256 = await _bounded_sha256(chunks, max_bytes=max_bytes)
    return DocumentVerificationView(
        status=(
            DocumentVerificationStatus.MATCH
            if candidate_sha256 == expected_sha256.lower()
            else DocumentVerificationStatus.NO_MATCH
        ),
        checked_at=checked_at,
    )


class PrivateDocumentVerificationService:
    def __init__(
        self,
        *,
        repository: DocumentProofRepository,
        access_policy: DocumentDeliveryAccessPolicy,
        gateway: DocumentEvidenceVerifier,
        max_bytes: int,
        clock: Callable[[], datetime] | None = None,
        record_result: Callable[
            [AuthPrincipal, UUID, DocumentVerificationStatus], Awaitable[None]
        ]
        | None = None,
    ) -> None:
        self._repository = repository
        self._access_policy = access_policy
        self._gateway = gateway
        self._max_bytes = max_bytes
        self._clock = clock or (lambda: datetime.now(UTC))
        self._record_result = record_result

    async def verify_public(
        self,
        *,
        expected_sha256: str | None,
        certificate_is_confirmed: bool,
        chunks: AsyncIterator[bytes],
    ) -> DocumentVerificationView:
        return await verify_public_document(
            expected_sha256=expected_sha256,
            certificate_is_confirmed=certificate_is_confirmed,
            chunks=chunks,
            max_bytes=self._max_bytes,
            clock=self._clock,
        )

    async def verify(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
        chunks: AsyncIterator[bytes],
    ) -> DocumentVerificationView:
        result = await self._verify(principal, media_id, chunks)
        if self._record_result is not None:
            await self._record_result(principal, media_id, result.status)
        return result

    async def _verify(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
        chunks: AsyncIterator[bytes],
    ) -> DocumentVerificationView:
        checked_at = self._clock()
        reference = await self._repository.find_by_media_id(media_id)
        policy_allowed = await self._access_policy.can_deliver(principal, media_id)
        if reference is None or (
            reference.owner_user_id != principal.user_id and not policy_allowed
        ):
            return self._result(DocumentVerificationStatus.NOT_AUTHORIZED, checked_at)
        if (
            reference.expected_sha256 is None
            or reference.evidence_status is None
            or reference.evidence_key is None
            or reference.commitment is None
        ):
            return self._result(
                DocumentVerificationStatus.PENDING_CONFIRMATION,
                checked_at,
            )
        if reference.evidence_status in {
            DocumentEvidenceStatus.QUEUED,
            DocumentEvidenceStatus.BROADCAST,
        }:
            return self._result(
                DocumentVerificationStatus.PENDING_CONFIRMATION,
                checked_at,
            )
        if reference.evidence_status is DocumentEvidenceStatus.FAILED:
            return self._result(
                DocumentVerificationStatus.CHAIN_UNAVAILABLE,
                checked_at,
            )
        if not self._proof_reference_is_consistent(reference):
            return self._result(DocumentVerificationStatus.NO_MATCH, checked_at)
        try:
            proof_matches = await self._gateway.verify_document_evidence(
                evidence_key=bytes.fromhex(reference.evidence_key),
                commitment=bytes.fromhex(reference.commitment),
            )
        except (BlockchainGatewayError, ValueError):
            return self._result(
                DocumentVerificationStatus.CHAIN_UNAVAILABLE,
                checked_at,
            )
        if not proof_matches:
            return self._result(DocumentVerificationStatus.NO_MATCH, checked_at)
        candidate_sha256 = await _bounded_sha256(chunks, max_bytes=self._max_bytes)
        return self._result(
            (
                DocumentVerificationStatus.MATCH
                if candidate_sha256 == reference.expected_sha256.lower()
                else DocumentVerificationStatus.NO_MATCH
            ),
            checked_at,
        )

    @staticmethod
    def _proof_reference_is_consistent(reference: DocumentProofReference) -> bool:
        if (
            reference.document_hash_claim_id is None
            or reference.version_no is None
            or reference.submitter_reference is None
            or reference.recorded_at is None
            or reference.expected_sha256 is None
            or reference.evidence_key is None
            or reference.commitment is None
        ):
            return False
        try:
            rebuilt = build_document_evidence_commitment(
                document_claim_id=reference.document_hash_claim_id,
                document_sha256=reference.expected_sha256,
                version=reference.version_no,
                submitter_reference=reference.submitter_reference,
                previous_evidence_key=reference.previous_evidence_key,
                recorded_at=reference.recorded_at,
            )
        except ValueError:
            return False
        return (
            rebuilt.evidence_key == reference.evidence_key
            and rebuilt.commitment == reference.commitment
        )

    @staticmethod
    def _result(
        status: DocumentVerificationStatus,
        checked_at: datetime,
    ) -> DocumentVerificationView:
        return DocumentVerificationView(status=status, checked_at=checked_at)
