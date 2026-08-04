import logging
from collections.abc import Callable, Collection
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.errors import (
    DossierForbiddenError,
    DossierInvalidStateError,
    DossierNotFoundError,
    DossierValidationError,
)
from app.modules.dossiers.models import (
    DossierEvidence,
    DossierStatus,
)
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.workflow import DossierWorkflowService
from app.modules.reviews.types import DossierTransitionView

logger = logging.getLogger(__name__)

SUPPLEMENT_REQUESTED_EVENT = "dossier.supplement_requested"
ADMIN_ROLES = frozenset({"SUPER_ADMIN"})


class PrecheckService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        payload_cipher: OutboxPayloadCipher,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._dossiers = DossierRepository(session)
        self._outbox = OutboxRepository(session)
        self._workflow = DossierWorkflowService(self._dossiers)
        self._payload_cipher = payload_cipher
        self._clock = clock or (lambda: datetime.now(UTC))

    async def start_precheck(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reason: str,
    ) -> DossierTransitionView:
        return await self._transition(
            principal,
            dossier_id,
            reason=reason,
            allowed_sources=(DossierStatus.SUBMITTED,),
            target=DossierStatus.PRECHECK,
            reason_code="ADMIN_PRECHECK_STARTED",
        )

    async def pass_precheck(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reason: str,
    ) -> DossierTransitionView:
        return await self._transition(
            principal,
            dossier_id,
            reason=reason,
            allowed_sources=(DossierStatus.PRECHECK,),
            target=DossierStatus.UNDER_REVIEW,
            reason_code="ADMIN_PRECHECK_PASSED",
        )

    async def request_supplement(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reason: str,
    ) -> DossierTransitionView:
        return await self._transition(
            principal,
            dossier_id,
            reason=reason,
            allowed_sources=(
                DossierStatus.PRECHECK,
                DossierStatus.UNDER_REVIEW,
            ),
            target=DossierStatus.NEEDS_SUPPLEMENT,
            reason_code="ADMIN_SUPPLEMENT_REQUESTED",
            clone_evidence=True,
            notify_owner=True,
        )

    async def _transition(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reason: str,
        allowed_sources: Collection[DossierStatus],
        target: DossierStatus,
        reason_code: str,
        clone_evidence: bool = False,
        notify_owner: bool = False,
    ) -> DossierTransitionView:
        self._require_admin(principal)
        normalized_reason = self._reason(reason)
        async with self._session.begin():
            dossier = await self._dossiers.get_by_id(dossier_id, for_update=True)
            if dossier is None:
                raise DossierNotFoundError()
            if dossier.status not in allowed_sources:
                raise DossierInvalidStateError(
                    f"Transition from {dossier.status.value} to "
                    f"{target.value} is not allowed."
                )
            if clone_evidence:
                await self._clone_current_evidence(dossier_id)
            self._workflow.transition(
                dossier,
                target=target,
                actor_user_id=principal.user_id,
                allowed_sources=allowed_sources,
                reason_code=reason_code,
                note=normalized_reason,
            )
            if notify_owner:
                self._add_supplement_event(
                    dossier_id=dossier.id,
                    owner_user_id=dossier.owner_user_id,
                    reason=normalized_reason,
                )
            await self._session.flush()
            result = DossierTransitionView(
                dossier_id=dossier.id,
                status=dossier.status,
            )
        self._audit(reason_code.lower(), principal.user_id, dossier_id)
        return result

    async def _clone_current_evidence(self, dossier_id: UUID) -> None:
        dossier = await self._dossiers.get_by_id(dossier_id)
        if dossier is None or dossier.current_version_no <= 0:
            raise DossierInvalidStateError(
                "A submitted dossier version is required for supplementation."
            )
        draft_rows = await self._dossiers.list_draft_evidences(dossier_id)
        if draft_rows:
            raise DossierInvalidStateError(
                "Dossier already contains unlocked supplement evidence."
            )
        version = await self._dossiers.get_version(
            dossier_id,
            dossier.current_version_no,
        )
        if version is None:
            raise DossierInvalidStateError(
                "The current dossier version could not be found."
            )
        rows = await self._dossiers.list_evidences(
            dossier_id,
            version_id=version.id,
        )
        if not rows:
            raise DossierInvalidStateError(
                "The current dossier version has no evidence."
            )
        for evidence, _ in rows:
            self._dossiers.add_evidence(
                DossierEvidence(
                    dossier_id=dossier_id,
                    dossier_version_id=None,
                    media_asset_id=evidence.media_asset_id,
                    evidence_type=evidence.evidence_type,
                    title=evidence.title,
                    description=evidence.description,
                    issued_at=evidence.issued_at,
                    display_order=evidence.display_order,
                    is_public=evidence.is_public,
                )
            )

    def _add_supplement_event(
        self,
        *,
        dossier_id: UUID,
        owner_user_id: UUID,
        reason: str,
    ) -> None:
        encrypted = self._payload_cipher.encrypt(
            {
                "dossier_id": str(dossier_id),
                "recipient_user_id": str(owner_user_id),
                "reason": reason,
            },
            event_type=SUPPLEMENT_REQUESTED_EVENT,
            aggregate_id=dossier_id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=SUPPLEMENT_REQUESTED_EVENT,
                aggregate_type="dossier",
                aggregate_id=dossier_id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=self._clock(),
            )
        )

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        if not ADMIN_ROLES.intersection(principal.roles):
            raise DossierForbiddenError()

    @staticmethod
    def _reason(value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 2_000:
            raise DossierValidationError(
                "Transition reason must contain between 1 and 2000 characters."
            )
        return normalized

    @staticmethod
    def _audit(action: str, user_id: UUID, dossier_id: UUID) -> None:
        logger.info(
            "security_audit",
            extra={
                "action": f"dossier.{action}",
                "user_id": str(user_id),
                "dossier_id": str(dossier_id),
            },
        )

    async def close(self) -> None:
        await self._session.close()
