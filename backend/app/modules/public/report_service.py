import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import AuthRepository, OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.errors import (
    ContentReportDuplicateError,
    ContentReportNotFoundError,
    ContentReportTransitionError,
    PublicWorkForbiddenError,
    PublicWorkNotFoundError,
)
from app.modules.public.models import (
    ContentReport,
    ContentReportReason,
    ContentReportStatus,
    PublicationStatus,
    PublicWorkVisibility,
)
from app.modules.public.report_repository import (
    ContentReportRepository,
    ContentReportRow,
)
from app.modules.users.security import SensitiveFieldCipher


@dataclass(frozen=True, slots=True)
class ContentReportInput:
    reason: ContentReportReason
    description: str | None
    reporter_email: str | None
    captcha_token: str | None


class CaptchaVerifier(Protocol):
    async def verify(self, token: str | None, client_ip: str) -> bool: ...


class DisabledCaptchaVerifier:
    async def verify(self, token: str | None, client_ip: str) -> bool:
        return True


class ContentReportService:
    ADMIN_ROLES = frozenset({"CONTENT_ADMIN", "SUPER_ADMIN"})

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit: AuditService,
        pii_cipher: SensitiveFieldCipher,
        outbox_cipher: OutboxPayloadCipher,
        captcha: CaptchaVerifier | None = None,
    ) -> None:
        self._session = session
        self._reports = ContentReportRepository(session)
        self._works = PublicWorkRepository(session)
        self._auth = AuthRepository(session)
        self._audit = audit
        self._pii_cipher = pii_cipher
        self._outbox_cipher = outbox_cipher
        self._outbox = OutboxRepository(session)
        self._captcha = captcha or DisabledCaptchaVerifier()

    async def submit(
        self,
        work_id: UUID,
        payload: ContentReportInput,
        *,
        principal: AuthPrincipal | None,
        client_ip: str,
        request_id: str,
    ) -> ContentReport:
        if not await self._captcha.verify(payload.captcha_token, client_ip):
            raise PublicWorkForbiddenError()
        description = self._clean(payload.description, 2_000)
        email = (
            payload.reporter_email.strip().lower() if payload.reporter_email else None
        )
        ip_hash = self._digest(client_ip)
        identity = str(principal.user_id) if principal else email or ip_hash
        dedup_key = self._digest(
            "|".join(
                (
                    str(work_id),
                    payload.reason.value,
                    description or "",
                    identity,
                    datetime.now(UTC).date().isoformat(),
                )
            )
        )
        try:
            async with self._session.begin():
                work = await self._works.get_by_id(work_id)
                if (
                    work is None
                    or work.publication_status is not PublicationStatus.PUBLISHED
                    or work.visibility
                    not in {PublicWorkVisibility.PUBLIC, PublicWorkVisibility.UNLISTED}
                ):
                    raise PublicWorkNotFoundError()
                if await self._reports.duplicate_exists(dedup_key):
                    raise ContentReportDuplicateError()
                report = ContentReport(
                    public_work_id=work.id,
                    reporter_user_id=principal.user_id if principal else None,
                    reporter_email_hash=self._digest(email) if email else None,
                    reporter_email_encrypted=(
                        self._pii_cipher.encrypt(email) if email else None
                    ),
                    reason=payload.reason,
                    description=description,
                    dedup_key=dedup_key,
                    reporter_ip_hash=ip_hash,
                )
                self._reports.add(report)
                await self._session.flush()
                self._audit.record(
                    actor_user_id=principal.user_id if principal else None,
                    action="content_report.created",
                    resource_type="content_report",
                    resource_id=str(report.id),
                    after={"work_id": str(work.id), "reason": report.reason.value},
                    request_id=request_id,
                    ip_hash=ip_hash,
                )
                recipients = await self._auth.list_user_ids_by_role_codes(
                    self.ADMIN_ROLES
                )
                for recipient_user_id in recipients:
                    self._event(
                        report,
                        "content_report.created",
                        recipient_user_id=recipient_user_id,
                    )
        except IntegrityError as exc:
            if "dedup" in str(exc.orig).lower():
                raise ContentReportDuplicateError() from exc
            raise
        return report

    async def list_admin(
        self,
        principal: AuthPrincipal,
        *,
        status: ContentReportStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[ContentReportRow, ...], int]:
        self._require_admin(principal)
        return await self._reports.list(
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def transition(
        self,
        principal: AuthPrincipal,
        report_id: UUID,
        *,
        status: ContentReportStatus,
        resolution_note: str | None,
        request_id: str,
    ) -> ContentReportRow:
        self._require_admin(principal)
        note = self._clean(resolution_note, 2_000)
        terminal = {
            ContentReportStatus.RESOLVED,
            ContentReportStatus.DISMISSED,
            ContentReportStatus.SUSPENDED,
        }
        async with self._session.begin():
            row = await self._reports.get(report_id, for_update=True)
            if row is None:
                raise ContentReportNotFoundError()
            current = row.report.status
            allowed = (
                current is ContentReportStatus.OPEN
                and status is ContentReportStatus.UNDER_REVIEW
            ) or (current is ContentReportStatus.UNDER_REVIEW and status in terminal)
            if not allowed or (status in terminal and not note):
                raise ContentReportTransitionError()
            before = current.value
            row.report.status = status
            row.report.assigned_to_user_id = principal.user_id
            row.report.resolution_note = note
            row.report.resolved_at = datetime.now(UTC) if status in terminal else None
            self._audit.record(
                actor_user_id=principal.user_id,
                action="content_report.transitioned",
                resource_type="content_report",
                resource_id=str(row.report.id),
                before={"status": before},
                after={"status": status.value},
                request_id=request_id,
            )
            self._event(row.report, "content_report.transitioned")
        return row

    async def get_admin(
        self, principal: AuthPrincipal, report_id: UUID
    ) -> ContentReportRow:
        self._require_admin(principal)
        row = await self._reports.get(report_id)
        if row is None:
            raise ContentReportNotFoundError()
        return row

    def _event(
        self,
        report: ContentReport,
        event_type: str,
        *,
        recipient_user_id: UUID | None = None,
    ) -> None:
        payload = {
            "content_report_id": str(report.id),
            "public_work_id": str(report.public_work_id),
            "status": report.status.value,
        }
        if recipient_user_id is not None:
            payload["user_id"] = str(recipient_user_id)
        encrypted = self._outbox_cipher.encrypt(
            payload,
            event_type=event_type,
            aggregate_id=report.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=event_type,
                aggregate_type="content_report",
                aggregate_id=report.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=datetime.now(UTC),
            )
        )

    @classmethod
    def _require_admin(cls, principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="public_content.manage", compatible_roles=cls.ADMIN_ROLES
            ),
            PublicWorkForbiddenError,
        )

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def _clean(value: str | None, max_length: int) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.replace("\x00", "").split()).strip()
        return normalized[:max_length] or None
