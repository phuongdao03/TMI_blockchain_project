import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.security import hash_verification_token
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import (
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.certificates.errors import (
    CertificateConflictError,
    CertificateForbiddenError,
    CertificateNotFoundError,
)
from app.modules.certificates.metadata import CertificateMetadataBuilder
from app.modules.certificates.repository import CertificateRepository
from app.modules.certificates.types import CertificateVersionView
from app.modules.council.models import CouncilCase, CouncilCaseDecision
from app.modules.dossiers.models import DossierVersion
from app.modules.dossiers.provenance import version_has_trusted_provenance
from app.modules.dossiers.repository import DossierRepository
from app.modules.public.share_service import canonical_public_origin

REQUEST_ROLES = frozenset({"USER"})
DECIDE_ROLES = frozenset({"SUPER_ADMIN"})
MIN_REASON_LENGTH = 20
MAX_REASON_LENGTH = 2_000


class CertificateVersionService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        metadata_builder: CertificateMetadataBuilder,
        audit: AuditService,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
        public_base_url: str = "http://localhost:3100",
        environment: str = "local",
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._session = session
        self._metadata_builder = metadata_builder
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._public_base_url = canonical_public_origin(
            public_base_url,
            allow_local_http=environment == "local",
        )
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._certificates = CertificateRepository(session)
        self._dossiers = DossierRepository(session)

    async def request(
        self,
        principal: AuthPrincipal,
        *,
        certificate_id: UUID,
        dossier_version_id: UUID,
        reason: str,
    ) -> CertificateVersionView:
        self._require_request(principal)
        normalized_reason = self._reason(reason, field="Change reason")
        now = self._clock()
        try:
            async with self._session.begin():
                row = await self._certificates.get(certificate_id)
                if row is None:
                    raise CertificateNotFoundError()
                if not await self._certificates.can_access(
                    certificate_id,
                    principal.user_id,
                ):
                    raise CertificateForbiddenError()
                certificate, active_version, dossier, _, _ = row
                if certificate.status is not CertificateStatus.ACTIVE:
                    raise CertificateConflictError(
                        "Only an active certificate can be corrected."
                    )
                if (
                    await self._certificates.get_open_version_request(certificate_id)
                    is not None
                ):
                    raise CertificateConflictError(
                        "A certificate correction is already being processed."
                    )
                target = await self._session.scalar(
                    select(DossierVersion).where(
                        DossierVersion.id == dossier_version_id,
                        DossierVersion.dossier_id == dossier.id,
                    )
                )
                if target is None:
                    raise CertificateConflictError(
                        "The dossier version does not belong to this certificate."
                    )
                active_dossier_version = await self._session.get(
                    DossierVersion,
                    active_version.dossier_version_id,
                )
                if (
                    active_dossier_version is None
                    or target.version_no <= active_dossier_version.version_no
                    or target.version_no != dossier.current_version_no
                ):
                    raise CertificateConflictError(
                        "A correction must use the latest newer dossier version."
                    )
                approved = await self._session.scalar(
                    select(CouncilCase.id).where(
                        CouncilCase.dossier_id == dossier.id,
                        CouncilCase.dossier_version_id == target.id,
                        CouncilCase.decision == CouncilCaseDecision.APPROVE,
                    )
                )
                if approved is None:
                    raise CertificateConflictError(
                        "The corrected dossier version requires council approval."
                    )
                evidence_rows = await self._dossiers.list_evidences(
                    dossier.id,
                    version_id=target.id,
                )
                if not version_has_trusted_provenance(target, evidence_rows):
                    raise CertificateConflictError(
                        "Correction evidence integrity must be reverified."
                    )
                next_version_no = certificate.current_version_no + 1
                metadata, metadata_hash = self._metadata_builder.build(
                    certificate_number=certificate.certificate_number,
                    certificate_version=next_version_no,
                    dossier_version=target.version_no,
                    snapshot=target.snapshot_json,
                    issued_at=certificate.issued_at,
                    expires_at=certificate.expires_at,
                )
                token = self._token_factory()
                qr_payload = (
                    f"{self._public_base_url}/verify/{quote(token, safe='-._~')}"
                )
                requested = CertificateVersion(
                    id=self._uuid_factory(),
                    certificate_id=certificate.id,
                    version_no=next_version_no,
                    predecessor_version_id=active_version.id,
                    dossier_version_id=target.id,
                    metadata_json=metadata,
                    metadata_hash=metadata_hash,
                    public_token_hash=hash_verification_token(token),
                    qr_payload=qr_payload,
                    status=CertificateVersionStatus.PENDING_APPROVAL,
                    change_reason=normalized_reason,
                    requested_by=principal.user_id,
                    requested_at=now,
                )
                self._certificates.add_version(requested)
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="certificate.version.requested",
                    resource_type="certificate_version",
                    resource_id=str(requested.id),
                    after={
                        "certificate_id": str(certificate.id),
                        "version_no": next_version_no,
                        "status": requested.status.value,
                    },
                )
                await self._session.flush()
                return self._view(requested)
        except IntegrityError as exc:
            raise CertificateConflictError(
                "A certificate correction is already being processed."
            ) from exc

    async def reject(
        self,
        principal: AuthPrincipal,
        version_id: UUID,
        *,
        reason: str,
    ) -> CertificateVersionView:
        self._require_decide(principal)
        normalized_reason = self._reason(reason, field="Rejection reason")
        async with self._session.begin():
            version = await self._certificates.get_version(
                version_id,
                for_update=True,
            )
            if version is None:
                raise CertificateNotFoundError()
            if version.status is not CertificateVersionStatus.PENDING_APPROVAL:
                raise CertificateConflictError(
                    "Only a pending certificate correction can be rejected."
                )
            if version.requested_by == principal.user_id:
                raise CertificateForbiddenError()
            before = version.status.value
            version.status = CertificateVersionStatus.REJECTED
            version.decided_by = principal.user_id
            version.decided_at = self._clock()
            version.rejection_reason = normalized_reason
            self._audit.record(
                actor_user_id=principal.user_id,
                action="certificate.version.rejected",
                resource_type="certificate_version",
                resource_id=str(version.id),
                before={"status": before},
                after={"status": version.status.value},
            )
            await self._session.flush()
            return self._view(version)

    async def approve(
        self,
        principal: AuthPrincipal,
        version_id: UUID,
    ) -> CertificateVersionView:
        self._require_decide(principal)
        async with self._session.begin():
            version = await self._certificates.get_version(version_id)
            if version is None:
                raise CertificateNotFoundError()
            if version.status not in {
                CertificateVersionStatus.PENDING_APPROVAL,
                CertificateVersionStatus.ANCHOR_PENDING,
            }:
                raise CertificateConflictError(
                    "Only a pending certificate correction can be approved."
                )
            if version.requested_by == principal.user_id:
                raise CertificateForbiddenError()
            was_pending = version.status is CertificateVersionStatus.PENDING_APPROVAL
        async with self._session.begin():
            anchored = await self._certificates.get_version(version_id, for_update=True)
            if anchored is None:
                raise CertificateNotFoundError()
            if anchored.status is CertificateVersionStatus.PENDING_APPROVAL:
                anchored.status = CertificateVersionStatus.ANCHOR_PENDING
                anchored.decided_by = principal.user_id
                anchored.decided_at = self._clock()
            if was_pending:
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="certificate.version.approved",
                    resource_type="certificate_version",
                    resource_id=str(anchored.id),
                    before={"status": CertificateVersionStatus.PENDING_APPROVAL.value},
                    after={"status": anchored.status.value},
                )
                await self._session.flush()
            return self._view(anchored)

    async def list_history(
        self,
        principal: AuthPrincipal,
        certificate_id: UUID,
    ) -> tuple[CertificateVersionView, ...]:
        self._require_read(principal)
        async with self._session.begin():
            if await self._certificates.get(certificate_id) is None:
                raise CertificateNotFoundError()
            if not await self._certificates.can_access(
                certificate_id,
                principal.user_id,
            ):
                raise CertificateForbiddenError()
            rows = await self._certificates.list_versions(certificate_id)
            return tuple(self._view(row) for row in rows)

    async def list_requests(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[CertificateVersionView, ...], int]:
        self._require_decide(principal)
        async with self._session.begin():
            rows, total = await self._certificates.list_version_requests(
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return tuple(self._view(row) for row in rows), total

    async def revoke(
        self,
        principal: AuthPrincipal,
        certificate_id: UUID,
        *,
        reason: str,
    ) -> CertificateVersionView:
        self._require_decide(principal)
        normalized_reason = self._reason(reason, field="Revocation reason")
        async with self._session.begin():
            row = await self._certificates.get(certificate_id)
            if row is None:
                raise CertificateNotFoundError()
            certificate, version, _, _, _ = row
            if certificate.status is CertificateStatus.REVOKED:
                raise CertificateConflictError("Certificate is already revoked.")
            open_version = await self._certificates.get_open_version_request(
                certificate_id
            )
            if open_version is not None:
                raise CertificateConflictError(
                    "Resolve the open certificate correction before revocation."
                )
            revoked_at = self._clock()
            certificate.status = CertificateStatus.REVOKED
            certificate.revoked_at = revoked_at
            certificate.revocation_reason_hash = hashlib.sha256(
                normalized_reason.encode("utf-8")
            ).hexdigest()
            version.status = CertificateVersionStatus.REVOKED
            version.revoked_at = revoked_at
            self._audit.record(
                actor_user_id=principal.user_id,
                action="certificate.revoked",
                resource_type="certificate",
                resource_id=str(certificate_id),
                after={
                    "version_no": version.version_no,
                    "reason": normalized_reason,
                    "mode": "database",
                },
            )
            await self._session.flush()
            return self._view(version)

    async def close(self) -> None:
        await self._session.close()

    @staticmethod
    def _reason(value: str, *, field: str) -> str:
        normalized = " ".join(value.split())
        if not MIN_REASON_LENGTH <= len(normalized) <= MAX_REASON_LENGTH:
            raise CertificateConflictError(
                f"{field} must contain between {MIN_REASON_LENGTH} and "
                f"{MAX_REASON_LENGTH} characters."
            )
        return normalized

    @staticmethod
    def _require_request(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="certificate.version.request",
                compatible_roles=REQUEST_ROLES,
            ),
            CertificateForbiddenError,
        )

    @staticmethod
    def _require_decide(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="certificate.version.decide",
                compatible_roles=DECIDE_ROLES,
            ),
            CertificateForbiddenError,
        )

    @staticmethod
    def _require_read(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="certificate.read",
                compatible_roles=REQUEST_ROLES | DECIDE_ROLES,
            ),
            CertificateForbiddenError,
        )

    @staticmethod
    def _view(version: CertificateVersion) -> CertificateVersionView:
        return CertificateVersionView(
            id=version.id,
            certificate_id=version.certificate_id,
            version_no=version.version_no,
            dossier_version_id=version.dossier_version_id,
            predecessor_version_id=version.predecessor_version_id,
            status=version.status,
            change_reason=version.change_reason,
            requested_by=version.requested_by,
            requested_at=version.requested_at,
            decided_by=version.decided_by,
            decided_at=version.decided_at,
            rejection_reason=version.rejection_reason,
            metadata_hash=version.metadata_hash,
            blockchain_transaction_id=version.blockchain_transaction_id,
            pdf_ready=version.pdf_media_id is not None,
            created_at=version.created_at,
        )
