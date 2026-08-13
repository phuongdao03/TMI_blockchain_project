from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.modules.blockchain.document_evidence import build_document_evidence_commitment


def test_document_evidence_commitment_matches_versioned_vector() -> None:
    result = build_document_evidence_commitment(
        document_claim_id=UUID("11111111-2222-4333-8444-555555555555"),
        document_sha256="ab" * 32,
        version=1,
        submitter_reference="cd" * 32,
        previous_evidence_key=None,
        recorded_at=datetime(2026, 8, 12, 9, 30, tzinfo=UTC),
    )

    assert result.evidence_key == (
        "283b10116915282871c555a914f04f68ec7c1093b56ed0a924718e6f7eec38ee"
    )
    assert result.commitment == (
        "bdfd35e7df691eb1e5949696b69d3259705ccffb1d7624b7a4f793f834f9be10"
    )
    assert result.recorded_at_epoch == 1_786_527_000


def test_document_evidence_commitment_is_sensitive_to_document_bytes() -> None:
    claim_id = UUID("11111111-2222-4333-8444-555555555555")
    recorded_at = datetime(2026, 8, 12, 9, 30, tzinfo=UTC)
    original = build_document_evidence_commitment(
        document_claim_id=claim_id,
        document_sha256="ab" * 32,
        version=1,
        submitter_reference="cd" * 32,
        previous_evidence_key=None,
        recorded_at=recorded_at,
    )
    modified = build_document_evidence_commitment(
        document_claim_id=claim_id,
        document_sha256="ac" * 32,
        version=1,
        submitter_reference="cd" * 32,
        previous_evidence_key=None,
        recorded_at=recorded_at,
    )

    assert original.evidence_key == modified.evidence_key
    assert original.commitment != modified.commitment


def test_document_evidence_commitment_rejects_invalid_lineage() -> None:
    with pytest.raises(ValueError, match="predecessor"):
        build_document_evidence_commitment(
            document_claim_id=UUID("11111111-2222-4333-8444-555555555555"),
            document_sha256="ab" * 32,
            version=2,
            submitter_reference="cd" * 32,
            previous_evidence_key=None,
            recorded_at=datetime(2026, 8, 12, 9, 30, tzinfo=UTC),
        )
