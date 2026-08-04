from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.activity import (
    ActivityCursor,
    ActivityCursorCodec,
    ActivityKind,
)
from app.modules.engagement.models import PublicWorkFavorite, PublicWorkShareEvent
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)


@dataclass(frozen=True, slots=True)
class ActivityListRow:
    activity_id: UUID
    kind: ActivityKind
    public_work_id: UUID
    slug: str
    title: str
    short_description: str
    channel: str | None
    created_at: datetime


class ActivityRepository:
    def __init__(
        self,
        session: AsyncSession,
        *,
        cursor_codec: ActivityCursorCodec | None = None,
    ) -> None:
        self._session = session
        self._cursor_codec = cursor_codec or ActivityCursorCodec()

    async def record_share(
        self,
        *,
        user_id: UUID,
        public_work_id: UUID,
        channel: str,
    ) -> None:
        self._session.add(
            PublicWorkShareEvent(
                id=uuid4(),
                user_id=user_id,
                public_work_id=public_work_id,
                channel=channel,
            )
        )

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[tuple[ActivityListRow, ...], str | None]:
        decoded = self._cursor_codec.decode(cursor) if cursor else None
        favorite_rows = await self._favorites(
            user_id=user_id,
            cursor=decoded,
            limit=limit,
        )
        share_rows = await self._shares(user_id=user_id, cursor=decoded, limit=limit)
        rows = sorted(
            (*favorite_rows, *share_rows),
            key=lambda row: (row.created_at, row.activity_id),
            reverse=True,
        )
        page = tuple(rows[:limit])
        next_cursor = None
        if len(rows) > limit and page:
            last = page[-1]
            next_cursor = self._cursor_codec.encode(
                ActivityCursor(
                    created_at=last.created_at,
                    activity_id=last.activity_id,
                )
            )
        return page, next_cursor

    async def _favorites(
        self,
        *,
        user_id: UUID,
        cursor: ActivityCursor | None,
        limit: int,
    ) -> tuple[ActivityListRow, ...]:
        filters = self._work_filters(
            user_id=user_id,
            cursor=cursor,
            model=PublicWorkFavorite,
        )
        rows = (
            await self._session.execute(
                select(PublicWorkFavorite, PublicWork)
                .join(PublicWork, PublicWork.id == PublicWorkFavorite.public_work_id)
                .where(*filters)
                .order_by(
                    PublicWorkFavorite.created_at.desc(),
                    PublicWorkFavorite.id.desc(),
                )
                .limit(limit)
            )
        ).all()
        return tuple(
            ActivityListRow(
                activity_id=favorite.id,
                kind=ActivityKind.FAVORITE,
                public_work_id=work.id,
                slug=work.slug,
                title=work.title,
                short_description=work.short_description,
                channel=None,
                created_at=favorite.created_at,
            )
            for favorite, work in rows
        )

    async def _shares(
        self,
        *,
        user_id: UUID,
        cursor: ActivityCursor | None,
        limit: int,
    ) -> tuple[ActivityListRow, ...]:
        filters = self._work_filters(
            user_id=user_id,
            cursor=cursor,
            model=PublicWorkShareEvent,
        )
        rows = (
            await self._session.execute(
                select(PublicWorkShareEvent, PublicWork)
                .join(PublicWork, PublicWork.id == PublicWorkShareEvent.public_work_id)
                .where(*filters)
                .order_by(
                    PublicWorkShareEvent.created_at.desc(),
                    PublicWorkShareEvent.id.desc(),
                )
                .limit(limit)
            )
        ).all()
        return tuple(
            ActivityListRow(
                activity_id=event.id,
                kind=ActivityKind.SHARE,
                public_work_id=work.id,
                slug=work.slug,
                title=work.title,
                short_description=work.short_description,
                channel=event.channel,
                created_at=event.created_at,
            )
            for event, work in rows
        )

    @staticmethod
    def _work_filters(
        *,
        user_id: UUID,
        cursor: ActivityCursor | None,
        model: Any,
    ) -> tuple[Any, ...]:
        filters: list[Any] = [
            model.user_id == user_id,
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.deleted_at.is_(None),
        ]
        if cursor is not None:
            filters.append(
                or_(
                    model.created_at < cursor.created_at,
                    (model.created_at == cursor.created_at)
                    & (model.id < cursor.activity_id),
                )
            )
        return tuple(filters)
