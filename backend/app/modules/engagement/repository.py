from datetime import date
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.models import PublicWorkEngagementDaily
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)


class EngagementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_published_public_work_id(self, slug: str) -> UUID | None:
        statement = select(PublicWork.id).where(
            PublicWork.slug == slug,
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.deleted_at.is_(None),
        )
        return cast(UUID | None, await self._session.scalar(statement))

    async def increment_view(self, *, public_work_id: UUID, metric_date: date) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(PublicWork)
                .where(
                    PublicWork.id == public_work_id,
                    PublicWork.publication_status == PublicationStatus.PUBLISHED,
                    PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                    PublicWork.deleted_at.is_(None),
                )
                .values(view_count=PublicWork.view_count + 1)
            ),
        )
        if result.rowcount != 1:
            return False
        bind = self._session.get_bind()
        dialect_insert = (
            sqlite_insert if bind.dialect.name == "sqlite" else postgresql_insert
        )
        statement = dialect_insert(PublicWorkEngagementDaily).values(
            public_work_id=public_work_id,
            metric_date=metric_date,
            unique_views=1,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["public_work_id", "metric_date"],
            set_={
                "unique_views": PublicWorkEngagementDaily.unique_views + 1,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(statement)
        return True

    async def increment_share(self, *, public_work_id: UUID, metric_date: date) -> bool:
        work_id = await self._session.scalar(
            select(PublicWork.id).where(
                PublicWork.id == public_work_id,
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.deleted_at.is_(None),
            )
        )
        if work_id is None:
            return False
        bind = self._session.get_bind()
        dialect_insert = (
            sqlite_insert if bind.dialect.name == "sqlite" else postgresql_insert
        )
        statement = dialect_insert(PublicWorkEngagementDaily).values(
            public_work_id=public_work_id,
            metric_date=metric_date,
            share_events=1,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["public_work_id", "metric_date"],
            set_={
                "share_events": PublicWorkEngagementDaily.share_events + 1,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(statement)
        return True

    async def increment_qr_scan(
        self,
        *,
        public_work_id: UUID,
        metric_date: date,
    ) -> None:
        bind = self._session.get_bind()
        dialect_insert = (
            sqlite_insert if bind.dialect.name == "sqlite" else postgresql_insert
        )
        statement = dialect_insert(PublicWorkEngagementDaily).values(
            public_work_id=public_work_id,
            metric_date=metric_date,
            qr_scans=1,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["public_work_id", "metric_date"],
            set_={
                "qr_scans": PublicWorkEngagementDaily.qr_scans + 1,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(statement)
