from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import UserProfile


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(
        self,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> UserProfile | None:
        statement = select(UserProfile).where(UserProfile.user_id == user_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(UserProfile | None, await self._session.scalar(statement))

    def add_profile(self, profile: UserProfile) -> None:
        self._session.add(profile)
