from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.models import PublicShareLink
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)


@dataclass(frozen=True, slots=True)
class ResolvedShareLink:
    id: UUID
    public_work_id: UUID
    slug: str


class ShareLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_for_work(self, public_work_id: UUID) -> PublicShareLink | None:
        statement = (
            select(PublicShareLink)
            .where(
                PublicShareLink.public_work_id == public_work_id,
                PublicShareLink.revoked_at.is_(None),
            )
            .order_by(PublicShareLink.created_at.desc(), PublicShareLink.id.desc())
            .limit(1)
        )
        return cast(PublicShareLink | None, await self._session.scalar(statement))

    def add(self, link: PublicShareLink) -> None:
        self._session.add(link)

    async def resolve_public(self, token_hash: str) -> ResolvedShareLink | None:
        row = await self._session.execute(
            select(PublicShareLink, PublicWork)
            .join(PublicWork, PublicWork.id == PublicShareLink.public_work_id)
            .where(
                PublicShareLink.token_hash == token_hash,
                PublicShareLink.revoked_at.is_(None),
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.deleted_at.is_(None),
            )
        )
        pair = row.one_or_none()
        if pair is None:
            return None
        link, work = pair
        return ResolvedShareLink(link.id, work.id, work.slug)

    async def revoke_active_for_work(
        self,
        *,
        public_work_id: UUID,
        revoked_at: datetime,
    ) -> bool:
        link = await self.active_for_work(public_work_id)
        if link is None:
            return False
        link.revoked_at = revoked_at
        return True
