import base64
import hashlib
import hmac
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.session_service import AuthPrincipal
from app.modules.auth.tokens import hash_opaque_token
from app.modules.engagement.errors import EngagementUnavailableError
from app.modules.engagement.models import PublicShareLink
from app.modules.engagement.repository import EngagementRepository
from app.modules.engagement.share_link_repository import ShareLinkRepository
from app.modules.public.errors import PublicWorkForbiddenError, PublicWorkNotFoundError


class QrDeduplicator(Protocol):
    async def accept(self, *, visitor: str, public_work_id: str) -> bool: ...


class QrShareLinkService:
    ADMIN_ROLES = frozenset({"CONTENT_ADMIN", "SUPER_ADMIN"})

    def __init__(
        self,
        session: AsyncSession,
        *,
        scans: QrDeduplicator,
        token_secret: str,
    ) -> None:
        self._session = session
        self._links = ShareLinkRepository(session)
        self._engagement = EngagementRepository(session)
        self._scans = scans
        self._token_secret = token_secret.encode()
        self._audit = AuditService(session)

    async def token_for_work(self, public_work_id: UUID) -> str:
        async with self._session.begin():
            active = await self._links.active_for_work(public_work_id)
            if active is not None:
                return self._token_for_link(active.id)
            link = PublicShareLink(
                id=uuid4(),
                public_work_id=public_work_id,
                token_hash="",
            )
            token = self._token_for_link(link.id)
            link.token_hash = hash_opaque_token(token)
            self._links.add(link)
            return token

    async def resolve_redirect(self, token: str, *, visitor: str) -> str:
        async with self._session.begin():
            resolved = await self._links.resolve_public(hash_opaque_token(token))
            if resolved is None:
                raise PublicWorkNotFoundError()
            try:
                accepted = await self._scans.accept(
                    visitor=visitor,
                    public_work_id=str(resolved.public_work_id),
                )
            except EngagementUnavailableError:
                accepted = False
            if accepted:
                await self._engagement.increment_qr_scan(
                    public_work_id=resolved.public_work_id,
                    metric_date=datetime.now(UTC).date(),
                )
            return resolved.slug

    async def revoke(self, principal: AuthPrincipal, *, public_work_id: UUID) -> bool:
        if self.ADMIN_ROLES.isdisjoint(principal.roles):
            raise PublicWorkForbiddenError()
        async with self._session.begin():
            revoked = await self._links.revoke_active_for_work(
                public_work_id=public_work_id,
                revoked_at=datetime.now(UTC),
            )
            if revoked:
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="public_share_link.revoked",
                    resource_type="public_work",
                    resource_id=str(public_work_id),
                    request_id=None,
                )
            return revoked

    def _token_for_link(self, link_id: UUID) -> str:
        digest = hmac.new(
            self._token_secret,
            f"public-share-link:{link_id}".encode(),
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
