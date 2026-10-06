from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import Certificate, CertificateContentDraft
from app.modules.certificates.errors import (
    CertificateConflictError,
    CertificateForbiddenError,
    CertificateNotFoundError,
)
from app.modules.certificates.metadata import draft_content_from_snapshot
from app.modules.certificates.schemas import (
    CertificateContentDraftData,
    CertificateContentRequest,
)
from app.modules.dossiers.models import Dossier, DossierStatus


async def reset_content_draft(
    session: AsyncSession, dossier_id: UUID, snapshot: dict[str, object]
) -> None:
    content = draft_content_from_snapshot(snapshot)
    draft = await session.get(CertificateContentDraft, dossier_id, with_for_update=True)
    if draft is None:
        session.add(
            CertificateContentDraft(dossier_id=dossier_id, content_json=content)
        )
    else:
        draft.content_json = content
        draft.confirmed_at = None
        draft.confirmed_by_user_id = None


class CertificateContentService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        enqueue_issue: Callable[[UUID], None] | None = None,
    ) -> None:
        self._session = session
        self._enqueue_issue = enqueue_issue
        self._audit = AuditService(session)

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="public_content.manage",
                compatible_roles=frozenset({"SUPER_ADMIN"}),
            ),
            CertificateForbiddenError,
        )

    @staticmethod
    def _view(
        dossier: Dossier, draft: CertificateContentDraft
    ) -> CertificateContentDraftData:
        return CertificateContentDraftData(
            dossier_id=dossier.id,
            dossier_code=dossier.code,
            dossier_title=dossier.title,
            dossier_status=dossier.status.value,
            content=CertificateContentRequest.model_validate(draft.content_json),
            confirmed_at=draft.confirmed_at,
        )

    async def list_drafts(
        self, principal: AuthPrincipal
    ) -> tuple[CertificateContentDraftData, ...]:
        self._require_admin(principal)
        async with self._session.begin():
            rows = await self._session.execute(
                select(Dossier, CertificateContentDraft)
                .join(
                    CertificateContentDraft,
                    CertificateContentDraft.dossier_id == Dossier.id,
                )
                .outerjoin(Certificate, Certificate.dossier_id == Dossier.id)
                .where(
                    Certificate.id.is_(None),
                    Dossier.status.in_(
                        (
                            DossierStatus.APPROVED,
                            DossierStatus.PAYMENT_PENDING,
                            DossierStatus.PAID,
                        )
                    ),
                )
                .order_by(Dossier.created_at, Dossier.id)
                .limit(100)
            )
            return tuple(self._view(dossier, draft) for dossier, draft in rows)

    async def _editable(
        self, dossier_id: UUID
    ) -> tuple[Dossier, CertificateContentDraft]:
        dossier = await self._session.get(Dossier, dossier_id, with_for_update=True)
        draft = await self._session.get(
            CertificateContentDraft, dossier_id, with_for_update=True
        )
        if dossier is None or draft is None:
            raise CertificateNotFoundError()
        if dossier.status not in {
            DossierStatus.APPROVED,
            DossierStatus.PAYMENT_PENDING,
            DossierStatus.PAID,
        }:
            raise CertificateConflictError("Certificate content is already frozen.")
        certificate_id = await self._session.scalar(
            select(Certificate.id).where(Certificate.dossier_id == dossier_id)
        )
        if certificate_id is not None:
            raise CertificateConflictError("Certificate content is already frozen.")
        return dossier, draft

    async def update(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        content: CertificateContentRequest,
    ) -> CertificateContentDraftData:
        self._require_admin(principal)
        normalized = CertificateContentRequest(
            title=content.title.strip(),
            summary=content.summary.strip(),
            subject=content.subject.strip(),
            category=content.category.strip(),
        )
        async with self._session.begin():
            dossier, draft = await self._editable(dossier_id)
            draft.content_json = normalized.model_dump()
            draft.confirmed_at = None
            draft.confirmed_by_user_id = None
            self._audit.record(
                actor_user_id=principal.user_id,
                action="certificate.content_updated",
                resource_type="dossier",
                resource_id=str(dossier_id),
                after=normalized.model_dump(),
            )
            return self._view(dossier, draft)

    async def confirm(
        self, principal: AuthPrincipal, dossier_id: UUID
    ) -> CertificateContentDraftData:
        self._require_admin(principal)
        async with self._session.begin():
            dossier, draft = await self._editable(dossier_id)
            CertificateContentRequest.model_validate(draft.content_json)
            draft.confirmed_at = datetime.now(UTC)
            draft.confirmed_by_user_id = principal.user_id
            should_issue = dossier.status is DossierStatus.PAID
            self._audit.record(
                actor_user_id=principal.user_id,
                action="certificate.content_confirmed",
                resource_type="dossier",
                resource_id=str(dossier_id),
                after={"confirmed_at": draft.confirmed_at.isoformat()},
            )
            result = self._view(dossier, draft)
        if should_issue and self._enqueue_issue is not None:
            self._enqueue_issue(dossier_id)
        return result
