import hashlib
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

EVIDENCE_KEY_DOMAIN = b"TMI:DOCUMENT:EVIDENCE:KEY:V1\0"
EVIDENCE_COMMITMENT_DOMAIN = b"TMI:DOCUMENT:EVIDENCE:COMMITMENT:V1\0"
ZERO_HASH = bytes(32)


@dataclass(frozen=True, slots=True)
class DocumentEvidenceCommitment:
    evidence_key: str
    commitment: str
    recorded_at_epoch: int


def build_document_evidence_commitment(
    *,
    document_claim_id: UUID,
    document_sha256: str,
    version: int,
    submitter_reference: str,
    previous_evidence_key: str | None,
    recorded_at: datetime,
) -> DocumentEvidenceCommitment:
    """Build the stable, PII-free bytes32 values sent to the registry."""
    document_hash = _required_hash(document_sha256, "document SHA-256")
    submitter = _required_hash(submitter_reference, "submitter reference")
    if version < 1 or version > 2**32 - 1:
        raise ValueError("Document evidence version is invalid.")
    if version == 1 and previous_evidence_key is not None:
        raise ValueError("Initial document evidence cannot have a predecessor.")
    if version > 1 and previous_evidence_key is None:
        raise ValueError("Versioned document evidence requires a predecessor.")
    predecessor = (
        ZERO_HASH
        if previous_evidence_key is None
        else _required_hash(previous_evidence_key, "predecessor evidence key")
    )
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise ValueError("Document evidence timestamp must include a timezone.")
    recorded_at_epoch = int(recorded_at.timestamp())
    if recorded_at_epoch <= 0 or recorded_at_epoch > 2**64 - 1:
        raise ValueError("Document evidence timestamp is invalid.")

    evidence_key = hashlib.sha256(
        EVIDENCE_KEY_DOMAIN + document_claim_id.bytes
    ).digest()
    commitment = hashlib.sha256(
        EVIDENCE_COMMITMENT_DOMAIN
        + evidence_key
        + document_hash
        + version.to_bytes(4, "big")
        + submitter
        + predecessor
        + recorded_at_epoch.to_bytes(8, "big")
    ).digest()
    return DocumentEvidenceCommitment(
        evidence_key=evidence_key.hex(),
        commitment=commitment.hex(),
        recorded_at_epoch=recorded_at_epoch,
    )


def _required_hash(value: str, label: str) -> bytes:
    if len(value) != 64 or value != value.lower():
        raise ValueError(f"{label.capitalize()} must be lowercase SHA-256 hex.")
    try:
        result = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(
            f"{label.capitalize()} must be lowercase SHA-256 hex."
        ) from exc
    if len(result) != 32:
        raise ValueError(f"{label.capitalize()} must be lowercase SHA-256 hex.")
    return result
