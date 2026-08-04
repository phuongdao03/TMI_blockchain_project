from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.session_service import AuthPrincipal
from app.modules.engagement.favorite_repository import (
    FavoriteListRow,
    FavoriteRepository,
)
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.errors import PublicWorkNotFoundError


class FavoriteRepositoryPort(Protocol):
    async def add_if_absent(self, *, user_id: UUID, public_work_id: UUID) -> bool: ...

    async def remove(self, *, user_id: UUID, public_work_id: UUID) -> bool: ...

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[tuple[FavoriteListRow, ...], int]: ...


class PublicWorkLookupPort(Protocol):
    async def find_published_public_id(self, slug: str) -> UUID | None: ...


class FavoriteService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        audit: AuditService,
        favorites: FavoriteRepositoryPort | None = None,
        works: PublicWorkLookupPort | None = None,
    ) -> None:
        self._session = session
        self._audit = audit
        self._favorites: FavoriteRepositoryPort = favorites or FavoriteRepository(
            session
        )
        self._works: PublicWorkLookupPort = works or PublicWorkRepository(session)

    async def add(
        self,
        principal: AuthPrincipal,
        *,
        slug: str,
        request_id: str,
    ) -> bool:
        async with self._session.begin():
            public_work_id = await self._published_public_id(slug)
            created = await self._favorites.add_if_absent(
                user_id=principal.user_id,
                public_work_id=public_work_id,
            )
            if created:
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="public_work.favorite_added",
                    resource_type="public_work",
                    resource_id=str(public_work_id),
                    after={"favorite": True},
                    request_id=request_id,
                )
            return created

    async def remove(
        self,
        principal: AuthPrincipal,
        *,
        slug: str,
        request_id: str,
    ) -> bool:
        async with self._session.begin():
            public_work_id = await self._published_public_id(slug)
            removed = await self._favorites.remove(
                user_id=principal.user_id,
                public_work_id=public_work_id,
            )
            if removed:
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="public_work.favorite_removed",
                    resource_type="public_work",
                    resource_id=str(public_work_id),
                    before={"favorite": True},
                    request_id=request_id,
                )
            return removed

    async def list_for_user(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[FavoriteListRow, ...], int]:
        async with self._session.begin():
            return await self._favorites.list_for_user(
                user_id=principal.user_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    async def _published_public_id(self, slug: str) -> UUID:
        public_work_id = await self._works.find_published_public_id(slug)
        if public_work_id is None:
            raise PublicWorkNotFoundError()
        return public_work_id
