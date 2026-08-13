import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.document_evidence import build_document_evidence_commitment
from app.modules.blockchain.gateway import BlockchainGatewayError
from app.modules.blockchain.models import DocumentEvidenceStatus
from app.modules.blockchain.verification import (
    DocumentProofReference,
    DocumentVerificationStatus,
    DocumentVerificationTooLargeError,
    PrivateDocumentVerificationService,
    verify_public_document,
)


async def _chunks(*values: bytes) -> AsyncIterator[bytes]:
    for value in values:
        yield value


class StubProofRepository:
    def __init__(self, reference: DocumentProofReference | None) -> None:
        self.reference = reference

    async def find_by_media_id(
        self,
        media_id: UUID,
    ) -> DocumentProofReference | None:
        return self.reference


class StubAccessPolicy:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    async def can_deliver(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> bool:
        return self.allowed


class StubGateway:
    def __init__(self, result: bool | Exception = True) -> None:
        self.result = result
        self.calls = 0

    async def verify_document_evidence(
        self,
        *,
        evidence_key: bytes,
        commitment: bytes,
    ) -> bool:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _principal(user_id: UUID | None = None) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id or uuid4(),
        session_id=uuid4(),
        email="applicant@example.test",
        roles=("APPLICANT",),
    )


def _reference(*, owner_user_id: UUID | None = None) -> DocumentProofReference:
    claim_id = uuid4()
    recorded_at = datetime(2026, 8, 12, 8, 0, tzinfo=UTC)
    expected_sha256 = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    proof = build_document_evidence_commitment(
        document_claim_id=claim_id,
        document_sha256=expected_sha256,
        version=1,
        submitter_reference="ef" * 32,
        previous_evidence_key=None,
        recorded_at=recorded_at,
    )
    return DocumentProofReference(
        media_asset_id=uuid4(),
        owner_user_id=owner_user_id or uuid4(),
        expected_sha256=expected_sha256,
        evidence_key=proof.evidence_key,
        commitment=proof.commitment,
        evidence_status=DocumentEvidenceStatus.CONFIRMED,
        document_hash_claim_id=claim_id,
        version_no=1,
        submitter_reference="ef" * 32,
        recorded_at=recorded_at,
    )


def test_public_document_comparison_matches_without_persisting_bytes() -> None:
    result = asyncio.run(
        verify_public_document(
            expected_sha256=(
                "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
            ),
            certificate_is_confirmed=True,
            chunks=_chunks(b"hel", b"lo"),
            max_bytes=16,
        )
    )

    assert result.status is DocumentVerificationStatus.MATCH
    assert result.checked_at.tzinfo is not None


def test_public_document_comparison_rejects_oversized_stream() -> None:
    with pytest.raises(DocumentVerificationTooLargeError):
        asyncio.run(
            verify_public_document(
                expected_sha256="ab" * 32,
                certificate_is_confirmed=True,
                chunks=_chunks(b"1234", b"5678"),
                max_bytes=7,
            )
        )


def test_private_verification_does_not_distinguish_missing_and_forbidden_ids() -> None:
    now = datetime(2026, 8, 12, 8, 0, tzinfo=UTC)
    missing = PrivateDocumentVerificationService(
        repository=StubProofRepository(None),
        access_policy=StubAccessPolicy(False),
        gateway=StubGateway(),
        max_bytes=16,
        clock=lambda: now,
    )
    forbidden = PrivateDocumentVerificationService(
        repository=StubProofRepository(_reference()),
        access_policy=StubAccessPolicy(False),
        gateway=StubGateway(),
        max_bytes=16,
        clock=lambda: now,
    )

    missing_result = asyncio.run(
        missing.verify(_principal(), uuid4(), _chunks(b"hello"))
    )
    forbidden_result = asyncio.run(
        forbidden.verify(_principal(), uuid4(), _chunks(b"hello"))
    )

    assert missing_result == forbidden_result
    assert missing_result.status is DocumentVerificationStatus.NOT_AUTHORIZED


def test_private_verification_reports_chain_unavailable_before_reading_file() -> None:
    owner_id = uuid4()
    gateway = StubGateway(BlockchainGatewayError("rpc unavailable"))
    service = PrivateDocumentVerificationService(
        repository=StubProofRepository(_reference(owner_user_id=owner_id)),
        access_policy=StubAccessPolicy(False),
        gateway=gateway,
        max_bytes=16,
    )

    result = asyncio.run(
        service.verify(_principal(owner_id), uuid4(), _chunks(b"hello"))
    )

    assert result.status is DocumentVerificationStatus.CHAIN_UNAVAILABLE
    assert gateway.calls == 1


def test_private_verification_reports_pending_and_mismatch_states() -> None:
    owner_id = uuid4()
    pending_reference = _reference(owner_user_id=owner_id)
    pending_reference = DocumentProofReference(
        media_asset_id=pending_reference.media_asset_id,
        owner_user_id=pending_reference.owner_user_id,
        expected_sha256=pending_reference.expected_sha256,
        evidence_key=pending_reference.evidence_key,
        commitment=pending_reference.commitment,
        evidence_status=DocumentEvidenceStatus.BROADCAST,
        document_hash_claim_id=pending_reference.document_hash_claim_id,
        version_no=pending_reference.version_no,
        submitter_reference=pending_reference.submitter_reference,
        previous_evidence_key=pending_reference.previous_evidence_key,
        recorded_at=pending_reference.recorded_at,
    )
    pending = PrivateDocumentVerificationService(
        repository=StubProofRepository(pending_reference),
        access_policy=StubAccessPolicy(False),
        gateway=StubGateway(),
        max_bytes=16,
    )
    mismatch = PrivateDocumentVerificationService(
        repository=StubProofRepository(_reference(owner_user_id=owner_id)),
        access_policy=StubAccessPolicy(False),
        gateway=StubGateway(),
        max_bytes=16,
    )

    pending_result = asyncio.run(
        pending.verify(_principal(owner_id), uuid4(), _chunks(b"hello"))
    )
    mismatch_result = asyncio.run(
        mismatch.verify(_principal(owner_id), uuid4(), _chunks(b"changed"))
    )

    assert pending_result.status is DocumentVerificationStatus.PENDING_CONFIRMATION
    assert mismatch_result.status is DocumentVerificationStatus.NO_MATCH
