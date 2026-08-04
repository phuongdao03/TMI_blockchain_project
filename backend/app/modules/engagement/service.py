from datetime import UTC, date, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.errors import EngagementUnavailableError
from app.modules.engagement.repository import EngagementRepository
from app.modules.public.errors import PublicWorkNotFoundError


class ViewDeduplicator(Protocol):
    async def accept(self, *, visitor: str, public_work_id: str) -> bool: ...


class ShareDeduplicator(Protocol):
    async def accept(
        self,
        *,
        visitor: str,
        public_work_id: str,
        channel: str,
    ) -> bool: ...


class EngagementRepositoryPort(Protocol):
    async def find_published_public_work_id(self, slug: str) -> UUID | None: ...

    async def increment_view(
        self,
        *,
        public_work_id: UUID,
        metric_date: date,
    ) -> bool: ...

    async def increment_share(
        self,
        *,
        public_work_id: UUID,
        metric_date: date,
    ) -> bool: ...


class EngagementService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        views: ViewDeduplicator,
        shares: ShareDeduplicator | None = None,
        repository: EngagementRepositoryPort | None = None,
    ) -> None:
        self._session = session
        self._repository: EngagementRepositoryPort = repository or EngagementRepository(
            session
        )
        self._views = views
        self._shares = shares

    async def record_view(self, *, slug: str, visitor: str) -> bool:
        async with self._session.begin():
            public_work_id = await self._repository.find_published_public_work_id(slug)
            if public_work_id is None:
                raise PublicWorkNotFoundError()
            accepted = await self._views.accept(
                visitor=visitor,
                public_work_id=str(public_work_id),
            )
            if not accepted:
                return False
            incremented = await self._repository.increment_view(
                public_work_id=public_work_id,
                metric_date=datetime.now(UTC).date(),
            )
            if not incremented:
                raise PublicWorkNotFoundError()
            return True

    async def record_share(
        self,
        *,
        slug: str,
        visitor: str,
        channel: str,
    ) -> bool:
        if self._shares is None:
            raise EngagementUnavailableError()
        async with self._session.begin():
            public_work_id = await self._repository.find_published_public_work_id(slug)
            if public_work_id is None:
                raise PublicWorkNotFoundError()
            accepted = await self._shares.accept(
                visitor=visitor,
                public_work_id=str(public_work_id),
                channel=channel,
            )
            if not accepted:
                return False
            incremented = await self._repository.increment_share(
                public_work_id=public_work_id,
                metric_date=datetime.now(UTC).date(),
            )
            if not incremented:
                raise PublicWorkNotFoundError()
            return True
