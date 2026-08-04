from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.engagement.activity_repository import (
    ActivityListRow,
    ActivityRepository,
)


class ActivityRepositoryPort(Protocol):
    async def list_for_user(
        self,
        *,
        user_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[tuple[ActivityListRow, ...], str | None]: ...


class ActivityService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repository: ActivityRepositoryPort | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or ActivityRepository(session)

    async def list_for_user(
        self,
        principal: AuthPrincipal,
        *,
        cursor: str | None,
        limit: int,
    ) -> tuple[tuple[ActivityListRow, ...], str | None]:
        async with self._session.begin():
            return await self._repository.list_for_user(
                user_id=principal.user_id,
                cursor=cursor,
                limit=limit,
            )
