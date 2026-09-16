import hashlib
import secrets
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.security import hash_verification_token
from app.modules.blockchain.models import (
    Certificate,
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.certificates.metadata import (
    CertificateMetadataBuilder,
    CertificateNumberingService,
)
from app.modules.public.models import PublicWork
from app.modules.public.share_service import canonical_public_origin

LEGACY_PREFIX = "TMI-"
REVOCATION_REASON = "CNS identity hard cutover and certificate reissuance"


@dataclass(frozen=True, slots=True)
class CertificateRebrandReport:
    candidates: int
    reissued: int
    replacement_version_ids: tuple[UUID, ...]


def replacement_metadata(
    source: dict[str, object],
    *,
    certificate_number: str,
    issued_at: datetime,
    expires_at: datetime,
) -> tuple[dict[str, object], str]:
    metadata = deepcopy(source)
    metadata["certificateNumber"] = certificate_number
    metadata["certificateVersion"] = 1
    metadata["issuedAt"] = issued_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    metadata["expiresAt"] = (
        expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    )
    dossier_code = metadata.get("dossierCode")
    if isinstance(dossier_code, str) and dossier_code.startswith(LEGACY_PREFIX):
        metadata["dossierCode"] = f"CNS-{dossier_code[len(LEGACY_PREFIX) :]}"
    asset = metadata.get("asset")
    if isinstance(asset, dict) and asset.get("subject") in {
        "Chủ thể hồ sơ TMI",
        "Chủ thể hồ sơ CNS",
    }:
        asset["subject"] = "Chưa công bố"
    digest = hashlib.sha256(
        CertificateMetadataBuilder.canonical_bytes(metadata)
    ).hexdigest()
    return metadata, digest


class CertificateRebrandService:
    """Revoke legacy certificates and issue replacements without rewriting history."""

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
            Certificate.certificate_number.startswith(LEGACY_PREFIX),
            Certificate.status != CertificateStatus.REVOKED,
        )
        replacement_version_ids: list[UUID] = []
        reason_hash = hashlib.sha256(REVOCATION_REASON.encode("utf-8")).hexdigest()
        async with self._session.begin():
            candidate_ids = tuple(
                await self._session.scalars(
                    select(Certificate.id).where(*criteria).order_by(Certificate.id)
                )
            )
            if dry_run or not candidate_ids:
                return CertificateRebrandReport(
                    candidates=len(candidate_ids),
                    reissued=0,
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
                if legacy.status is CertificateStatus.REVOKED:
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

                now = datetime.now(UTC)
                legacy.status = CertificateStatus.REVOKED
                legacy.revoked_at = now
                legacy.revocation_reason_hash = reason_hash
                version.status = CertificateVersionStatus.REVOKED
                version.revoked_at = now

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
                        public_token_hash=token_hash,
                        qr_payload=qr_payload,
                        status=CertificateVersionStatus.ACTIVE,
                        change_reason=REVOCATION_REASON,
                        blockchain_transaction_id=version.blockchain_transaction_id,
                    )
                )
                await self._session.execute(
                    update(PublicWork)
                    .where(PublicWork.certificate_id == legacy.id)
                    .values(certificate_id=replacement_id)
                )
                replacement_version_ids.append(replacement_version_id)

            await self._session.flush()

        return CertificateRebrandReport(
            candidates=len(candidate_ids),
            reissued=len(replacement_version_ids),
            replacement_version_ids=tuple(replacement_version_ids),
        )
