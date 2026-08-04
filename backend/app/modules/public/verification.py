import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.modules.blockchain.gateway import (
    BlockchainGatewayError,
    CertificateRecord,
)
from app.modules.blockchain.models import CertificateStatus
from app.modules.certificates.metadata import CertificateMetadataBuilder
from app.modules.dossiers.canonical import snapshot_sha256


class VerificationStatus(StrEnum):
    VALID = "VALID"
    MISMATCH = "MISMATCH"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    PENDING = "PENDING"
    NOT_FOUND = "NOT_FOUND"


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
    network: str | None
    contract_address: str | None
    transaction_hash: str | None
    confirmations: int
    confirmed_at: datetime | None


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


class VerificationEvaluator:
    @staticmethod
    def evaluate(
        *,
        local_status: CertificateStatus,
        local_metadata_hash: str,
        local_dossier_hash: str,
        local_version: int,
        expires_at: datetime | None,
        chain_record: CertificateRecord,
        now: datetime,
    ) -> VerificationStatus:
        if local_status is CertificateStatus.REVOKED or chain_record.revoked:
            return VerificationStatus.REVOKED
        if (
            local_status is CertificateStatus.EXPIRED
            or (expires_at is not None and expires_at <= now)
            or (
                chain_record.expires_at > 0
                and chain_record.expires_at <= now.timestamp()
            )
        ):
            return VerificationStatus.EXPIRED
        if (
            chain_record.metadata_hash.hex() != local_metadata_hash.lower()
            or chain_record.dossier_hash.hex() != local_dossier_hash.lower()
            or chain_record.version != local_version
        ):
            return VerificationStatus.MISMATCH
        return VerificationStatus.VALID


class CertificateReader(Protocol):
    async def get_certificate(self, certificate_id: bytes) -> CertificateRecord: ...


ContextFinder = Callable[[str], Awaitable[VerificationContext | None]]


class VerificationCache(Protocol):
    async def get(self, key: str) -> CertificateRecord | None: ...

    async def set(self, key: str, record: CertificateRecord) -> None: ...


class PublicVerificationService:
    def __init__(
        self,
        *,
        gateway: CertificateReader,
        find_by_token: ContextFinder,
        find_by_number: ContextFinder,
        find_by_transaction: ContextFinder,
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

    async def verify_token(self, token: str) -> VerificationView:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return await self._verify(await self._find_by_token(token_hash))

    async def verify_number(self, certificate_number: str) -> VerificationView:
        return await self._verify(
            await self._find_by_number(certificate_number.strip().upper())
        )

    async def verify_transaction(self, transaction_hash: str) -> VerificationView:
        return await self._verify(
            await self._find_by_transaction(transaction_hash.strip().lower())
        )

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
            certificate_key = hashlib.sha256(
                context.certificate_number.encode()
            ).hexdigest()
            record = (
                await self._cache.get(certificate_key)
                if self._cache is not None
                else None
            )
            if record is None:
                record = await self._gateway.get_certificate(
                    bytes.fromhex(certificate_key)
                )
        except BlockchainGatewayError:
            status = VerificationStatus.PENDING
        else:
            status = VerificationEvaluator.evaluate(
                local_status=context.certificate_status,
                local_metadata_hash=metadata_hash,
                local_dossier_hash=dossier_hash,
                local_version=context.version,
                expires_at=context.expires_at,
                chain_record=record,
                now=now,
            )
            if (
                status is VerificationStatus.VALID
                and not local_integrity_matches
            ):
                status = VerificationStatus.MISMATCH
            if (
                status is VerificationStatus.VALID
                and self._cache is not None
            ):
                await self._cache.set(certificate_key, record)
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
        )
