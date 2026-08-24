import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher, hash_verification_token
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.certificates.errors import (
    CertificateConflictError,
    CertificateForbiddenError,
    CertificateGenerationError,
    CertificateNotFoundError,
)
from app.modules.certificates.metadata import (
    CertificateMetadataBuilder,
    CertificateNumberingService,
)
from app.modules.certificates.pdf import CertificatePdfRenderer
from app.modules.certificates.repository import (
    CertificateRepository,
    CertificateRow,
)
from app.modules.certificates.storage import CertificateStorage
from app.modules.certificates.types import (
    CertificateDetailView,
    CertificateDownloadView,
    CertificateView,
)
from app.modules.dossiers.models import DossierStatus, DossierVersion
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.workflow import DossierWorkflowService
from app.modules.media.gateway import MediaGateway
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.share_service import canonical_public_origin

CERTIFICATE_ISSUED_EVENT = "certificate.issued"
CERTIFICATE_ROLES = frozenset({"USER", "SUPER_ADMIN"})


class CertificateService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        media_gateway: MediaGateway,
        storage: CertificateStorage,
        renderer: CertificatePdfRenderer,
        metadata_builder: CertificateMetadataBuilder,
        numbering: CertificateNumberingService,
        payload_cipher: OutboxPayloadCipher,
        public_base_url: str,
        environment: str,
        delivery_ttl_seconds: int,
        validity_days: int,
        blockchain_service: BlockchainTransactionService | None = None,
        enqueue_issue: Callable[[UUID], None] | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._session = session
        self._media_gateway = media_gateway
        self._storage = storage
        self._renderer = renderer
        self._metadata_builder = metadata_builder
        self._numbering = numbering
        self._payload_cipher = payload_cipher
        self._public_base_url = canonical_public_origin(
            public_base_url,
            allow_local_http=environment == "local",
        )
        self._environment = environment
        self._delivery_ttl_seconds = delivery_ttl_seconds
        self._validity_days = validity_days
        self._blockchain = blockchain_service
        self._enqueue_issue = enqueue_issue
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._certificates = CertificateRepository(session)
        self._audit_service = AuditService(session)
        self._dossiers = DossierRepository(session)
        self._workflow = DossierWorkflowService(self._dossiers)
        self._outbox = OutboxRepository(session)

    async def list(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[CertificateView, ...], int]:
        self._require_role(principal)
        async with self._session.begin():
            rows, total = await self._certificates.list_accessible(
                principal.user_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return tuple(self._view(row) for row in rows), total

    async def get(
        self,
        principal: AuthPrincipal,
        certificate_id: UUID,
    ) -> CertificateDetailView:
        self._require_role(principal)
        async with self._session.begin():
            row = await self._certificates.get(certificate_id)
            if row is None:
                raise CertificateNotFoundError()
            if not await self._certificates.can_access(
                certificate_id,
                principal.user_id,
            ):
                raise CertificateForbiddenError()
            certificate, version, *_ = row
            return CertificateDetailView(
                certificate=self._view(row),
                metadata=dict(version.metadata_json),
                metadata_hash=version.metadata_hash,
                qr_payload=version.qr_payload or certificate.qr_payload,
            )

    async def download(
        self,
        principal: AuthPrincipal,
        certificate_id: UUID,
    ) -> CertificateDownloadView:
        self._require_role(principal)
        async with self._session.begin():
            row = await self._certificates.get(certificate_id)
            if row is None:
                raise CertificateNotFoundError()
            if not await self._certificates.can_access(
                certificate_id,
                principal.user_id,
            ):
                raise CertificateForbiddenError()
            certificate = row[0]
            if certificate.pdf_media_id is None:
                raise CertificateConflictError("Certificate PDF is not ready.")
            media = await self._session.get(MediaAsset, certificate.pdf_media_id)
            if media is None or media.status is not MediaStatus.ACTIVE:
                raise CertificateConflictError("Certificate PDF is not available.")
            expires_at = int(self._clock().timestamp()) + self._delivery_ttl_seconds
            url = self._media_gateway.create_signed_delivery_url(
                public_id=media.cloudinary_public_id,
                resource_type=media.resource_type,
                file_format="pdf",
                expires_at=expires_at,
            )
            self._audit(
                "certificate.download.signed",
                certificate_id,
                actor_user_id=principal.user_id,
                status=certificate.status,
                pdf_ready=True,
            )
        return CertificateDownloadView(url=url, expires_at=expires_at)

    async def process_issuance(self, dossier_id: UUID) -> CertificateView | None:
        async with self._session.begin():
            dossier = await self._dossiers.get_by_id(dossier_id, for_update=True)
            if dossier is None:
                raise CertificateNotFoundError()
            certificate = await self._certificates.get_by_dossier(
                dossier_id,
                for_update=True,
            )
            status = dossier.status
            actor_user_id = dossier.owner_user_id
        if certificate is None and status is DossierStatus.PAID:
            certificate = await self._prepare_certificate(dossier_id)
            if self._blockchain is None:
                raise CertificateConflictError("Blockchain service is unavailable.")
            await self._blockchain.request_certificate_anchor(
                certificate_id=certificate.id,
                actor_user_id=actor_user_id,
            )
            return None
        if status is DossierStatus.ANCHOR_PENDING:
            return None
        if certificate is None:
            raise CertificateConflictError(
                "Certificate issuance context is unavailable."
            )
        if status is DossierStatus.CERTIFICATE_ISSUED:
            row = await self._required_row(certificate.id)
            return self._view(row)
        if status is not DossierStatus.ANCHORED:
            raise CertificateConflictError(
                "Dossier is not ready for certificate issuance."
            )
        return await self._render_and_finalize(certificate.id)

    async def render_version(self, certificate_version_id: UUID) -> None:
        """Render the confirmed current version without changing anchored metadata."""
        async with self._session.begin():
            version = await self._certificates.get_version(certificate_version_id)
            if version is None:
                raise CertificateNotFoundError()
            certificate = await self._session.get(Certificate, version.certificate_id)
            if certificate is None:
                raise CertificateNotFoundError()
            dossier = await self._dossiers.get_by_id(certificate.dossier_id)
            transaction = (
                await self._session.get(
                    BlockchainTransaction,
                    version.blockchain_transaction_id,
                )
                if version.blockchain_transaction_id is not None
                else None
            )
            if dossier is None:
                raise CertificateNotFoundError()
            if (
                version.status is not CertificateVersionStatus.ACTIVE
                or certificate.current_version_no != version.version_no
                or transaction is None
                or transaction.status is not BlockchainTransactionStatus.CONFIRMED
                or transaction.tx_hash is None
            ):
                raise CertificateConflictError(
                    "Certificate version is not ready for rendition."
                )
            if version.pdf_media_id is not None:
                return
            display_metadata = {
                **version.metadata_json,
                "blockchain": {
                    "network": transaction.network,
                    "contractAddress": transaction.contract_address,
                    "transactionHash": transaction.tx_hash,
                },
            }
            verification_url = version.qr_payload or certificate.qr_payload
            version_no = version.version_no
            certificate_number = certificate.certificate_number
            owner_user_id = dossier.owner_user_id
            certificate_id = certificate.id
        try:
            rendered = self._renderer.render(
                metadata=display_metadata,
                verification_url=verification_url,
            )
            stored = await self._storage.upload_pdf(
                public_id=(
                    f"ip-certificate/{self._environment}/certificates/"
                    f"{certificate_id}/v{version_no}"
                ),
                content=rendered.content,
            )
        except Exception as exc:
            raise CertificateGenerationError(
                "Certificate PDF generation failed."
            ) from exc
        async with self._session.begin():
            locked_version = await self._certificates.get_version(
                certificate_version_id,
                for_update=True,
            )
            locked_certificate = await self._session.get(
                Certificate,
                certificate_id,
                with_for_update=True,
            )
            if locked_version is None or locked_certificate is None:
                raise CertificateNotFoundError()
            if locked_version.pdf_media_id is not None:
                return
            if (
                locked_version.status is not CertificateVersionStatus.ACTIVE
                or locked_certificate.current_version_no != locked_version.version_no
            ):
                raise CertificateConflictError(
                    "Certificate version changed before rendition completed."
                )
            media = MediaAsset(
                id=self._uuid_factory(),
                owner_user_id=owner_user_id,
                cloudinary_public_id=stored.public_id,
                cloudinary_version=stored.version,
                resource_type="raw",
                access_mode="authenticated",
                original_filename=f"{certificate_number}-v{version_no}.pdf",
                mime_type="application/pdf",
                bytes=stored.bytes,
                sha256=stored.sha256,
                status=MediaStatus.ACTIVE,
            )
            self._session.add(media)
            locked_version.pdf_media_id = media.id
            locked_certificate.pdf_media_id = media.id
            self._audit(
                "certificate.version.rendered",
                certificate_version_id,
                actor_service="certificate-issuance-worker",
                resource_type="certificate_version",
                pdf_ready=True,
            )
            await self._session.flush()

    async def _prepare_certificate(self, dossier_id: UUID) -> Certificate:
        issued_at = self._clock()
        certificate_id = self._uuid_factory()
        token = self._token_factory()
        async with self._session.begin():
            replay = await self._certificates.get_by_dossier(
                dossier_id,
                for_update=True,
            )
            if replay is not None:
                return replay
            dossier = await self._dossiers.get_by_id(dossier_id, for_update=True)
            if dossier is None or dossier.status is not DossierStatus.PAID:
                raise CertificateConflictError(
                    "Only a paid dossier can prepare a certificate."
                )
            # The dossier row is the issuance mutex. Recheck after acquiring it
            # so two workers cannot create two certificates for one dossier.
            replay = await self._certificates.get_by_dossier(
                dossier_id,
                for_update=True,
            )
            if replay is not None:
                return replay
            version = await self._session.scalar(
                select(DossierVersion).where(
                    DossierVersion.dossier_id == dossier.id,
                    DossierVersion.version_no == dossier.current_version_no,
                )
            )
            if version is None:
                raise CertificateConflictError(
                    "Approved dossier version is unavailable."
                )
            number = self._numbering.generate(certificate_id, issued_at)
            expires_at = issued_at + timedelta(days=self._validity_days)
            qr_payload = f"{self._public_base_url}/verify/{quote(token, safe='-._~')}"
            metadata, metadata_hash = self._metadata_builder.build(
                certificate_number=number,
                certificate_version=1,
                dossier_version=version.version_no,
                snapshot=version.snapshot_json,
                issued_at=issued_at,
                expires_at=expires_at,
            )
            certificate = Certificate(
                id=certificate_id,
                certificate_number=number,
                dossier_id=dossier.id,
                current_version_no=1,
                status=CertificateStatus.ACTIVE,
                issued_at=issued_at,
                expires_at=expires_at,
                public_token_hash=hash_verification_token(token),
                qr_payload=qr_payload,
            )
            self._certificates.add(certificate)
            self._certificates.add_version(
                CertificateVersion(
                    certificate_id=certificate.id,
                    version_no=1,
                    dossier_version_id=version.id,
                    metadata_json=metadata,
                    metadata_hash=metadata_hash,
                    public_token_hash=certificate.public_token_hash,
                    qr_payload=certificate.qr_payload,
                    status=CertificateVersionStatus.ACTIVE,
                )
            )
            self._audit(
                "certificate.prepared",
                certificate.id,
                actor_service="certificate-issuance-worker",
                status=certificate.status,
                pdf_ready=False,
            )
            await self._session.flush()
            return certificate

    async def _render_and_finalize(
        self,
        certificate_id: UUID,
    ) -> CertificateView:
        row = await self._required_row(certificate_id)
        certificate, version, dossier, _, transaction = row
        if certificate.pdf_media_id is not None:
            return self._view(row)
        if (
            transaction is None
            or transaction.status is not BlockchainTransactionStatus.CONFIRMED
            or transaction.tx_hash is None
        ):
            raise CertificateConflictError("Blockchain anchor is not confirmed.")
        display_metadata = {
            **version.metadata_json,
            "blockchain": {
                "network": transaction.network,
                "contractAddress": transaction.contract_address,
                "transactionHash": transaction.tx_hash,
            },
        }
        try:
            rendered = self._renderer.render(
                metadata=display_metadata,
                verification_url=version.qr_payload or certificate.qr_payload,
            )
            stored = await self._storage.upload_pdf(
                public_id=(
                    f"ip-certificate/{self._environment}/certificates/"
                    f"{certificate.id}/v{certificate.current_version_no}"
                ),
                content=rendered.content,
            )
        except Exception as exc:
            raise CertificateGenerationError(
                "Certificate PDF generation failed."
            ) from exc
        async with self._session.begin():
            locked = await self._certificates.get_by_dossier(
                dossier.id,
                for_update=True,
            )
            if locked is None:
                raise CertificateNotFoundError()
            if locked.pdf_media_id is None:
                media = MediaAsset(
                    id=self._uuid_factory(),
                    owner_user_id=dossier.owner_user_id,
                    cloudinary_public_id=stored.public_id,
                    cloudinary_version=stored.version,
                    resource_type="raw",
                    access_mode="authenticated",
                    original_filename=f"{certificate.certificate_number}.pdf",
                    mime_type="application/pdf",
                    bytes=stored.bytes,
                    sha256=stored.sha256,
                    status=MediaStatus.ACTIVE,
                )
                self._session.add(media)
                locked.pdf_media_id = media.id
                version.pdf_media_id = media.id
                active_dossier = await self._dossiers.get_by_id(
                    dossier.id,
                    for_update=True,
                )
                if (
                    active_dossier is not None
                    and active_dossier.status is DossierStatus.ANCHORED
                ):
                    self._workflow.transition(
                        active_dossier,
                        target=DossierStatus.CERTIFICATE_ISSUED,
                        actor_user_id=active_dossier.owner_user_id,
                        allowed_sources={DossierStatus.ANCHORED},
                        reason_code="CERTIFICATE_ISSUED",
                    )
                self._add_issued_event(locked, dossier.owner_user_id)
                self._audit(
                    "certificate.issued",
                    locked.id,
                    actor_service="certificate-issuance-worker",
                    status=locked.status,
                    pdf_ready=True,
                )
                await self._session.flush()
        final_row = await self._required_row(certificate_id)
        return self._view(final_row)

    async def _required_row(self, certificate_id: UUID) -> CertificateRow:
        async with self._session.begin():
            row = await self._certificates.get(certificate_id)
            if row is None:
                raise CertificateNotFoundError()
            return row

    def _add_issued_event(self, certificate: Certificate, user_id: UUID) -> None:
        encrypted = self._payload_cipher.encrypt(
            {
                "certificate_id": str(certificate.id),
                "certificate_number": certificate.certificate_number,
                "recipient_user_id": str(user_id),
            },
            event_type=CERTIFICATE_ISSUED_EVENT,
            aggregate_id=certificate.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=CERTIFICATE_ISSUED_EVENT,
                aggregate_type="certificate",
                aggregate_id=certificate.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=self._clock(),
            )
        )

    @staticmethod
    def _view(row: CertificateRow) -> CertificateView:
        certificate, _, dossier, category, transaction = row
        return CertificateView(
            id=certificate.id,
            certificate_number=certificate.certificate_number,
            dossier_id=dossier.id,
            dossier_code=dossier.code,
            asset_title=dossier.title,
            category_name=category.name,
            current_version_no=certificate.current_version_no,
            status=certificate.status,
            issued_at=certificate.issued_at,
            expires_at=certificate.expires_at,
            pdf_ready=certificate.pdf_media_id is not None,
            network=transaction.network if transaction is not None else None,
            contract_address=(
                transaction.contract_address if transaction is not None else None
            ),
            transaction_hash=(transaction.tx_hash if transaction is not None else None),
            blockchain_status=(transaction.status if transaction is not None else None),
            confirmations=(transaction.confirmations if transaction is not None else 0),
        )

    @staticmethod
    def _require_role(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="certificate.read", compatible_roles=CERTIFICATE_ROLES
            ),
            CertificateForbiddenError,
        )

    def _audit(
        self,
        action: str,
        resource_id: UUID,
        *,
        actor_user_id: UUID | None = None,
        actor_service: str | None = None,
        resource_type: str = "certificate",
        status: CertificateStatus | None = None,
        pdf_ready: bool | None = None,
    ) -> None:
        after: dict[str, object] = {}
        if status is not None:
            after["status"] = status.value
        if pdf_ready is not None:
            after["pdf_ready"] = pdf_ready
        self._audit_service.record(
            actor_user_id=actor_user_id,
            actor_service=actor_service,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            after=after or None,
        )
