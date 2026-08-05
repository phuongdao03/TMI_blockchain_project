from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.analytics_types import EngagementAnalyticsSnapshotView
from app.modules.engagement.models import (
    EngagementAnalyticsSnapshot,
    PublicWorkEngagementDaily,
    PublicWorkFavorite,
)
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)


class EngagementAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_snapshot(
        self,
        metric_date: date,
    ) -> EngagementAnalyticsSnapshotView | None:
        row = await self._session.scalar(
            select(EngagementAnalyticsSnapshot).where(
                EngagementAnalyticsSnapshot.metric_date == metric_date
            )
        )
        return self._view(row) if row is not None else None

    async def aggregate(self, metric_date: date) -> dict[str, int]:
        day_start = datetime.combine(metric_date, time.min, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        daily = await self._session.execute(
            select(
                func.coalesce(func.sum(PublicWorkEngagementDaily.unique_views), 0),
                func.coalesce(func.sum(PublicWorkEngagementDaily.share_events), 0),
                func.coalesce(func.sum(PublicWorkEngagementDaily.qr_scans), 0),
                func.coalesce(func.sum(PublicWorkEngagementDaily.report_requests), 0),
            ).where(PublicWorkEngagementDaily.metric_date == metric_date)
        )
        unique_views, share_events, qr_scans, report_requests = daily.one()
        favorite_events = await self._session.scalar(
            select(func.count(PublicWorkFavorite.id))
            .join(PublicWork, PublicWork.id == PublicWorkFavorite.public_work_id)
            .where(
                PublicWorkFavorite.created_at >= day_start,
                PublicWorkFavorite.created_at < day_end,
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.deleted_at.is_(None),
            )
        )
        return {
            "unique_views": int(unique_views or 0),
            "share_events": int(share_events or 0),
            "qr_scans": int(qr_scans or 0),
            "report_requests": int(report_requests or 0),
            "favorite_events": int(favorite_events or 0),
        }

    async def create_snapshot(
        self,
        *,
        metric_date: date,
        metrics: dict[str, int],
    ) -> EngagementAnalyticsSnapshotView:
        bind = self._session.get_bind()
        dialect_insert = (
            sqlite_insert if bind.dialect.name == "sqlite" else postgresql_insert
        )
        statement = dialect_insert(EngagementAnalyticsSnapshot).values(
            id=uuid4(),
            metric_date=metric_date,
            **metrics,
        )
        statement = statement.on_conflict_do_nothing(
            index_elements=["metric_date"],
        )
        await self._session.execute(statement)
        row = await self.get_snapshot(metric_date)
        if row is None:
            raise RuntimeError("Analytics snapshot was not persisted.")
        return row

    @staticmethod
    def _view(row: EngagementAnalyticsSnapshot) -> EngagementAnalyticsSnapshotView:
        return EngagementAnalyticsSnapshotView(
            id=row.id,
            metric_date=row.metric_date,
            generated_at=row.generated_at,
            unique_views=row.unique_views,
            share_events=row.share_events,
            qr_scans=row.qr_scans,
            report_requests=row.report_requests,
            favorite_events=row.favorite_events,
        )
