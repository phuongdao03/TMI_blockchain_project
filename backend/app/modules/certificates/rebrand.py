import hashlib
import secrets
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.security import hash_verification_token
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.certificates.metadata import (
    CertificateMetadataBuilder,
    CertificateNumberingService,
)
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.share_service import canonical_public_origin

LEGACY_PREFIXES = ("TMI-", "CNS-")
REVOCATION_REASON = "Tinh Hoa Viet certificate reissued with a THV number"


@dataclass(frozen=True, slots=True)
class CertificateRebrandReport:
    candidates: int
    prepared: int
    replacement_version_ids: tuple[UUID, ...]


def replacement_metadata(
    source: dict[str, object],
    *,
    certificate_number: str,
    issued_at: datetime,
    expires_at: datetime,
    author_display_name: str | None = None,
) -> tuple[dict[str, object], str]:
    metadata = deepcopy(source)
    metadata["certificateNumber"] = certificate_number
    metadata["certificateVersion"] = 1
    metadata["issuedAt"] = issued_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    metadata["expiresAt"] = (
        expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    )
    asset = metadata.get("asset")
    if isinstance(asset, dict):
        if author_display_name and author_display_name.strip():
            asset["subject"] = author_display_name.strip()
        elif asset.get("subject") in {
            "Chủ thể hồ sơ TMI",
            "Chủ thể hồ sơ CNS",
        }:
            asset["subject"] = "Chưa công bố"
    digest = hashlib.sha256(
        CertificateMetadataBuilder.canonical_bytes(metadata)
    ).hexdigest()
    return metadata, digest


class CertificateRebrandService:
    """Prepare THV replacements; legacy numbers stay live until PDF cutover."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        public_base_url: str,
        environment: str,
        validity_days: int,
    ) -> None:
        self._session = session
        self._public_base_url = canonical_public_origin(
            public_base_url,
            allow_local_http=environment == "local",
        )
        self._validity_days = validity_days
        self._numbering = CertificateNumberingService()

    async def run(self, *, dry_run: bool) -> CertificateRebrandReport:
        criteria = (
            or_(
                *(
                    Certificate.certificate_number.startswith(prefix)
                    for prefix in LEGACY_PREFIXES
                )
            ),
            Certificate.status == CertificateStatus.ACTIVE,
        )
        replacement_version_ids: list[UUID] = []
        async with self._session.begin():
            candidate_ids = tuple(
                await self._session.scalars(
                    select(Certificate.id).where(*criteria).order_by(Certificate.id)
                )
            )
            if dry_run or not candidate_ids:
                return CertificateRebrandReport(
                    candidates=len(candidate_ids),
                    prepared=0,
                    replacement_version_ids=(),
                )
            certificates = tuple(
                await self._session.scalars(
                    select(Certificate)
                    .where(Certificate.id.in_(candidate_ids))
                    .order_by(Certificate.id)
                    .with_for_update()
                )
            )
            for legacy in certificates:
                # A concurrent cutover may have completed while this runner was
                # waiting for the row lock. Never create a second replacement.
                if legacy.status is not CertificateStatus.ACTIVE:
                    continue
                existing = await self._session.scalar(
                    select(Certificate.id).where(
                        Certificate.dossier_id == legacy.dossier_id,
                        Certificate.certificate_number.startswith("THV-"),
                    )
                )
                if existing is not None:
                    continue
                version = await self._session.scalar(
                    select(CertificateVersion).where(
                        CertificateVersion.certificate_id == legacy.id,
                        CertificateVersion.version_no == legacy.current_version_no,
                    )
                )
                if version is None:
                    raise RuntimeError(
                        f"Legacy certificate {legacy.id} has no current version."
                    )

                if version.status is not CertificateVersionStatus.ACTIVE:
                    raise RuntimeError(f"Legacy certificate {legacy.id} is not active.")
                proof_transaction = await self._session.scalar(
                    select(BlockchainTransaction)
                    .where(
                        BlockchainTransaction.dossier_version_id
                        == version.dossier_version_id,
                        BlockchainTransaction.method == "recordProof",
                        BlockchainTransaction.status
                        == BlockchainTransactionStatus.CONFIRMED,
                        BlockchainTransaction.tx_hash.is_not(None),
                    )
                    .order_by(BlockchainTransaction.confirmed_at.desc())
                )
                if proof_transaction is None:
                    raise RuntimeError(
                        f"Legacy certificate {legacy.id} has no confirmed THV "
                        "dossier proof. Reissue requires a verified recordProof."
                    )
                public_work = await self._session.scalar(
                    select(PublicWork).where(PublicWork.dossier_id == legacy.dossier_id)
                )
                now = datetime.now(UTC)
                replacement_id = uuid4()
                replacement_version_id = uuid4()
                token = secrets.token_urlsafe(32)
                token_hash = hash_verification_token(token)
                number = self._numbering.generate(replacement_id, now)
                expires_at = now + timedelta(days=self._validity_days)
                qr_payload = (
                    f"{self._public_base_url}/verify/{quote(token, safe='-._~')}"
                )
                metadata, metadata_hash = replacement_metadata(
                    version.metadata_json,
                    certificate_number=number,
                    issued_at=now,
                    expires_at=expires_at,
                    author_display_name=(
                        public_work.author_display_name
                        if public_work is not None
                        and public_work.publication_status
                        is PublicationStatus.PUBLISHED
                        and public_work.visibility is PublicWorkVisibility.PUBLIC
                        and public_work.published_at is not None
                        else None
                    ),
                )
                self._session.add(
                    Certificate(
                        id=replacement_id,
                        certificate_number=number,
                        dossier_id=legacy.dossier_id,
                        current_version_no=1,
                        status=CertificateStatus.ACTIVE,
                        issued_at=now,
                        expires_at=expires_at,
                        public_token_hash=token_hash,
                        qr_payload=qr_payload,
                    )
                )
                self._session.add(
                    CertificateVersion(
                        id=replacement_version_id,
                        certificate_id=replacement_id,
                        version_no=1,
                        dossier_version_id=version.dossier_version_id,
                        metadata_json=metadata,
                        metadata_hash=metadata_hash,
                        blockchain_transaction_id=proof_transaction.id,
                        public_token_hash=token_hash,
                        qr_payload=qr_payload,
                        status=CertificateVersionStatus.ANCHOR_PENDING,
                        change_reason=REVOCATION_REASON,
                    )
                )
                replacement_version_ids.append(replacement_version_id)
                await self._session.flush()

            await self._session.flush()

        return CertificateRebrandReport(
            candidates=len(candidate_ids),
            prepared=len(replacement_version_ids),
            replacement_version_ids=tuple(replacement_version_ids),
        )

    async def ready_to_render(self) -> tuple[UUID, ...]:
        """Return staged THV versions for the existing PDF worker."""
        async with self._session.begin():
            return tuple(
                await self._session.scalars(
                    select(CertificateVersion.id)
                    .join(
                        Certificate, Certificate.id == CertificateVersion.certificate_id
                    )
                    .join(
                        BlockchainTransaction,
                        BlockchainTransaction.id
                        == CertificateVersion.blockchain_transaction_id,
                    )
                    .where(
                        Certificate.certificate_number.startswith("THV-"),
                        CertificateVersion.status
                        == CertificateVersionStatus.ANCHOR_PENDING,
                        CertificateVersion.change_reason == REVOCATION_REASON,
                        BlockchainTransaction.method == "recordProof",
                        BlockchainTransaction.status
                        == BlockchainTransactionStatus.CONFIRMED,
                    )
                )
            )
