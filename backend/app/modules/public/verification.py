import hashlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.blockchain.models import CertificateStatus
from app.modules.blockchain.proof_registry_gateway import THVProofRecord
from app.modules.blockchain.proof_registry_service import derive_thv_asset_id
from app.modules.blockchain.transport import BlockchainGatewayError
from app.modules.certificates.metadata import (
    PUBLIC_EVIDENCE_SCOPES,
    CertificateMetadataBuilder,
)
from app.modules.dossiers.canonical import snapshot_sha256


class VerificationStatus(StrEnum):
    VALID = "VALID"
    MISMATCH = "MISMATCH"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    PENDING = "PENDING"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True, slots=True)
class PublicEvidenceProof:
    title: str
    evidence_type: str
    sha256: str


@dataclass(frozen=True, slots=True)
class PublicEvidenceMetadata:
    """Safe, scope-qualified evidence metadata from a certificate snapshot."""

    title: str
    evidence_type: str
    sha256: str
    access_scope: str


def public_evidence_metadata(
    metadata: dict[str, object],
) -> tuple[PublicEvidenceMetadata, ...]:
    """Project only explicitly public, well-formed document metadata.

    Certificates created before access scopes were recorded are intentionally
    omitted: ``isPublic`` alone is not an authority to disclose an attachment.
    """
    values = metadata.get("publicEvidences")
    if not isinstance(values, list):
        return ()
    evidences: list[PublicEvidenceMetadata] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        title = value.get("title")
        evidence_type = value.get("type")
        digest = value.get("sha256")
        access_scope = value.get("accessScope")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(evidence_type, str)
            or not evidence_type.strip()
            or not isinstance(digest, str)
            or not isinstance(access_scope, str)
            or access_scope not in PUBLIC_EVIDENCE_SCOPES
            or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None
        ):
            continue
        evidences.append(
            PublicEvidenceMetadata(
                title=title.strip()[:255],
                evidence_type=evidence_type.strip()[:64],
                sha256=digest.lower(),
                access_scope=access_scope,
            )
        )
    return tuple(evidences)


def public_evidence_proofs(
    metadata: dict[str, object],
) -> tuple[PublicEvidenceProof, ...]:
    return tuple(
        PublicEvidenceProof(
            title=evidence.title,
            evidence_type=evidence.evidence_type,
            sha256=evidence.sha256,
        )
        for evidence in public_evidence_metadata(metadata)
    )


@dataclass(frozen=True, slots=True)
class VerificationContext:
    certificate_id: UUID
    certificate_number: str
    certificate_status: CertificateStatus
    asset_title: str
    category_name: str
    issued_at: datetime
    expires_at: datetime | None
    metadata_hash: str
    dossier_hash: str
    metadata: dict[str, object]
    dossier_snapshot: dict[str, object]
    version: int
    proof_version: int
    dossier_id: UUID
    network: str | None
    contract_address: str | None
    transaction_hash: str | None
    confirmations: int
    confirmed_at: datetime | None
    dossier_code: str | None = None
    block_number: int | None = None
    is_current_version: bool = True


@dataclass(frozen=True, slots=True)
class VerificationView:
    status: VerificationStatus
    checked_at: datetime
    certificate_number: str | None = None
    asset_title: str | None = None
    category_name: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    version: int | None = None
    network: str | None = None
    contract_address: str | None = None
    transaction_hash: str | None = None
    confirmations: int = 0
    confirmed_at: datetime | None = None
    explorer_url: str | None = None
    dossier_code: str | None = None
    metadata_hash: str | None = None
    block_number: int | None = None
    issuer_label: str | None = None
    documents: tuple[PublicEvidenceProof, ...] = ()


class VerificationEvaluator:
    @staticmethod
    def evaluate(
        *,
        local_status: CertificateStatus,
        local_dossier_hash: str,
        proof_version: int,
        expires_at: datetime | None,
        chain_record: THVProofRecord,
        now: datetime,
    ) -> VerificationStatus:
        if local_status is CertificateStatus.REVOKED:
            return VerificationStatus.REVOKED
        if local_status is CertificateStatus.EXPIRED or (
            expires_at is not None and expires_at <= now
        ):
            return VerificationStatus.EXPIRED
        if (
            not chain_record.exists
            or chain_record.proof_hash.hex() != local_dossier_hash.lower()
            or chain_record.version != proof_version
        ):
            return VerificationStatus.MISMATCH
        return VerificationStatus.VALID


class CertificateReader(Protocol):
    async def get_proof(self, asset_id: bytes, version: int) -> THVProofRecord: ...


ContextFinder = Callable[[str], Awaitable[VerificationContext | None]]


class VerificationCache(Protocol):
    async def get(self, key: str) -> THVProofRecord | None: ...

    async def set(self, key: str, record: THVProofRecord) -> None: ...


class PublicVerificationService:
    def __init__(
        self,
        *,
        gateway: CertificateReader,
        find_by_token: ContextFinder,
        find_by_number: ContextFinder,
        find_by_transaction: ContextFinder,
        audit: AuditService,
        audit_session: AsyncSession,
        explorer_base_url: str | None = None,
        cache: VerificationCache | None = None,
    ) -> None:
        self._gateway = gateway
        self._find_by_token = find_by_token
        self._find_by_number = find_by_number
        self._find_by_transaction = find_by_transaction
        self._explorer_base_url = (
            explorer_base_url.rstrip("/") if explorer_base_url else None
        )
        self._cache = cache
        self._audit = audit
        self._audit_session = audit_session

    async def verify_token(self, token: str) -> VerificationView:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        context = await self._find_by_token(token_hash)
        return await self._complete(
            await self._verify(context),
            context=context,
            lookup_type="token",
        )

    async def verify_number(self, certificate_number: str) -> VerificationView:
        context = await self._find_by_number(certificate_number.strip().upper())
        return await self._complete(
            await self._verify(context),
            context=context,
            lookup_type="certificate_number",
        )

    async def verify_transaction(self, transaction_hash: str) -> VerificationView:
        context = await self._find_by_transaction(transaction_hash.strip().lower())
        return await self._complete(
            await self._verify(context),
            context=context,
            lookup_type="transaction_hash",
        )

    async def _complete(
        self,
        result: VerificationView,
        *,
        context: VerificationContext | None,
        lookup_type: str,
    ) -> VerificationView:
        self._audit.record(
            actor_user_id=None,
            action="public.verification.completed",
            resource_type="certificate_verification",
            resource_id=str(context.certificate_id) if context else "unresolved",
            after={"lookup_type": lookup_type, "status": result.status.value},
        )
        await self._audit_session.commit()
        return result

    async def _verify(
        self,
        context: VerificationContext | None,
    ) -> VerificationView:
        now = datetime.now(UTC)
        if context is None:
            return VerificationView(
                status=VerificationStatus.NOT_FOUND,
                checked_at=now,
            )
        try:
            canonical_metadata = {
                key: value
                for key, value in context.metadata.items()
                if key != "rendition"
            }
            metadata_hash = hashlib.sha256(
                CertificateMetadataBuilder.canonical_bytes(canonical_metadata)
            ).hexdigest()
            dossier_hash = snapshot_sha256(context.dossier_snapshot)
            local_integrity_matches = (
                metadata_hash == context.metadata_hash.lower()
                and dossier_hash == context.dossier_hash.lower()
            )
            asset_id = derive_thv_asset_id(context.dossier_id)
            cache_key = f"{asset_id.hex()}:v{context.proof_version}"
            record = (
                await self._cache.get(cache_key) if self._cache is not None else None
            )
            if record is None:
                record = await self._gateway.get_proof(asset_id, context.proof_version)
        except BlockchainGatewayError:
            status = VerificationStatus.PENDING
        else:
            status = VerificationEvaluator.evaluate(
                local_status=context.certificate_status,
                local_dossier_hash=dossier_hash,
                proof_version=context.proof_version,
                expires_at=context.expires_at,
                chain_record=record,
                now=now,
            )
            if status is VerificationStatus.VALID and not local_integrity_matches:
                status = VerificationStatus.MISMATCH
            if status is VerificationStatus.VALID and self._cache is not None:
                await self._cache.set(cache_key, record)
        return VerificationView(
            status=status,
            checked_at=now,
            certificate_number=context.certificate_number,
            asset_title=context.asset_title,
            category_name=context.category_name,
            issued_at=context.issued_at,
            expires_at=context.expires_at,
            version=context.version,
            network=context.network,
            contract_address=context.contract_address,
            transaction_hash=context.transaction_hash,
            confirmations=context.confirmations,
            confirmed_at=context.confirmed_at,
            explorer_url=(
                f"{self._explorer_base_url}/tx/{context.transaction_hash}"
                if self._explorer_base_url and context.transaction_hash
                else None
            ),
            dossier_code=context.dossier_code,
            metadata_hash=context.metadata_hash,
            block_number=context.block_number,
            issuer_label="TMI Certificate",
            documents=public_evidence_proofs(context.metadata),
        )
