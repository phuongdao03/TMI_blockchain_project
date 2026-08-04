from collections.abc import Sequence
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search.history_models import (
    SearchHistoryEntry,
    SearchHistoryPreference,
)


class SearchHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def preference(
        self,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> SearchHistoryPreference | None:
        statement = select(SearchHistoryPreference).where(
            SearchHistoryPreference.user_id == user_id
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(
            SearchHistoryPreference | None,
            await self._session.scalar(statement),
        )

    def add_preference(self, preference: SearchHistoryPreference) -> None:
        self._session.add(preference)

    async def entry_by_hash(
        self,
        user_id: UUID,
        query_hash: str,
        *,
        for_update: bool = False,
    ) -> SearchHistoryEntry | None:
        statement = select(SearchHistoryEntry).where(
            SearchHistoryEntry.user_id == user_id,
            SearchHistoryEntry.query_hash == query_hash,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(SearchHistoryEntry | None, await self._session.scalar(statement))

    def add_entry(self, entry: SearchHistoryEntry) -> None:
        self._session.add(entry)

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int,
    ) -> Sequence[SearchHistoryEntry]:
        return (
            await self._session.scalars(
                select(SearchHistoryEntry)
                .where(SearchHistoryEntry.user_id == user_id)
                .order_by(
                    SearchHistoryEntry.searched_at.desc(),
                    SearchHistoryEntry.id.asc(),
                )
                .limit(limit)
            )
        ).all()

    async def clear(self, user_id: UUID) -> int:
        result = cast(
            CursorResult[object],
            await self._session.execute(
                delete(SearchHistoryEntry).where(SearchHistoryEntry.user_id == user_id)
            ),
        )
        return int(result.rowcount or 0)

    async def purge_before(self, cutoff: datetime) -> int:
        result = cast(
            CursorResult[object],
            await self._session.execute(
                delete(SearchHistoryEntry).where(
                    SearchHistoryEntry.searched_at < cutoff
                )
            ),
        )
        return int(result.rowcount or 0)
