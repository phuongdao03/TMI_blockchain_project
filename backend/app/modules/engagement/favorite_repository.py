from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.models import PublicWorkFavorite
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)


@dataclass(frozen=True, slots=True)
class FavoriteListRow:
    favorite_id: UUID
    public_work_id: UUID
    slug: str
    title: str
    short_description: str
    created_at: datetime


class FavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, *, user_id: UUID, public_work_id: UUID) -> bool:
        bind = self._session.get_bind()
        dialect_insert = (
            sqlite_insert if bind.dialect.name == "sqlite" else postgresql_insert
        )
        statement = dialect_insert(PublicWorkFavorite).values(
            id=uuid4(),
            user_id=user_id,
            public_work_id=public_work_id,
        )
        statement = statement.on_conflict_do_nothing(
            index_elements=["user_id", "public_work_id"],
        )
        result = cast(
            CursorResult[Any],
            await self._session.execute(statement),
        )
        return result.rowcount == 1

    async def remove(self, *, user_id: UUID, public_work_id: UUID) -> bool:
        statement = delete(PublicWorkFavorite).where(
            PublicWorkFavorite.user_id == user_id,
            PublicWorkFavorite.public_work_id == public_work_id,
        )
        result = cast(
            CursorResult[Any],
            await self._session.execute(statement),
        )
        return result.rowcount == 1

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[tuple[FavoriteListRow, ...], int]:
        filters = (
            PublicWorkFavorite.user_id == user_id,
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.deleted_at.is_(None),
        )
        statement = (
            select(PublicWorkFavorite, PublicWork)
            .join(PublicWork, PublicWork.id == PublicWorkFavorite.public_work_id)
            .where(*filters)
            .order_by(
                PublicWorkFavorite.created_at.desc(),
                PublicWorkFavorite.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        total = await self._session.scalar(
            select(func.count())
            .select_from(PublicWorkFavorite)
            .join(PublicWork, PublicWork.id == PublicWorkFavorite.public_work_id)
            .where(*filters)
        )
        return (
            tuple(
                FavoriteListRow(
                    favorite_id=favorite.id,
                    public_work_id=work.id,
                    slug=work.slug,
                    title=work.title,
                    short_description=work.short_description,
                    created_at=favorite.created_at,
                )
                for favorite, work in rows
            ),
            int(total or 0),
        )
