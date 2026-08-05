from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.models import (
    EngagementVelocitySnapshot,
    EngagementVelocitySnapshotItem,
    PublicWorkEngagementDaily,
    PublicWorkFavorite,
)
from app.modules.engagement.velocity_types import (
    EngagementVelocityDaily,
    EngagementVelocityItem,
    EngagementVelocitySnapshotDraft,
    EngagementVelocitySnapshotView,
)
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)


class EngagementVelocityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_window(
        self,
        *,
        window_start: date,
        window_end: date,
    ) -> EngagementVelocitySnapshotView | None:
        snapshot = await self._session.scalar(
            select(EngagementVelocitySnapshot).where(
                EngagementVelocitySnapshot.window_start == window_start,
                EngagementVelocitySnapshot.window_end == window_end,
            )
        )
        if snapshot is None:
            return None
        items = tuple(
            await self._session.scalars(
                select(EngagementVelocitySnapshotItem)
                .where(EngagementVelocitySnapshotItem.snapshot_id == snapshot.id)
                .order_by(EngagementVelocitySnapshotItem.display_order)
            )
        )
        return EngagementVelocitySnapshotView(
            id=snapshot.id,
            window_start=snapshot.window_start,
            window_end=snapshot.window_end,
            formula_version=snapshot.formula_version,
            generated_at=snapshot.generated_at,
            items=tuple(self._item_view(item) for item in items),
        )

    async def list_daily_candidates(
        self,
        *,
        window_start: date,
        window_end: date,
    ) -> tuple[EngagementVelocityDaily, ...]:
        daily_rows = (
            await self._session.execute(
                select(
                    PublicWorkEngagementDaily.public_work_id,
                    PublicWorkEngagementDaily.metric_date,
                    PublicWorkEngagementDaily.unique_views,
                    PublicWorkEngagementDaily.share_events,
                    PublicWorkEngagementDaily.qr_scans,
                    PublicWork.category_id,
                )
                .join(
                    PublicWork,
                    PublicWork.id == PublicWorkEngagementDaily.public_work_id,
                )
                .where(
                    PublicWorkEngagementDaily.metric_date >= window_start,
                    PublicWorkEngagementDaily.metric_date <= window_end,
                    PublicWork.publication_status == PublicationStatus.PUBLISHED,
                    PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                    PublicWork.deleted_at.is_(None),
                )
            )
        ).all()
        rows: dict[tuple[object, date], EngagementVelocityDaily] = {
            (row.public_work_id, row.metric_date): EngagementVelocityDaily(
                work_id=row.public_work_id,
                category_id=row.category_id,
                metric_date=row.metric_date,
                views=int(row.unique_views),
                shares=int(row.share_events),
                qr_scans=int(row.qr_scans),
                favorites=0,
            )
            for row in daily_rows
        }

        day_start = datetime.combine(window_start, time.min, tzinfo=UTC)
        day_end = datetime.combine(window_end + timedelta(days=1), time.min, tzinfo=UTC)
        favorite_rows = (
            await self._session.execute(
                select(
                    PublicWorkFavorite.public_work_id,
                    PublicWorkFavorite.created_at,
                    PublicWork.category_id,
                )
                .join(PublicWork, PublicWork.id == PublicWorkFavorite.public_work_id)
                .where(
                    PublicWorkFavorite.created_at >= day_start,
                    PublicWorkFavorite.created_at < day_end,
                    PublicWork.publication_status == PublicationStatus.PUBLISHED,
                    PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                    PublicWork.deleted_at.is_(None),
                )
            )
        ).all()
        for row in favorite_rows:
            created_at = row.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            metric_date = created_at.astimezone(UTC).date()
            key = (row.public_work_id, metric_date)
            current = rows.get(key)
            if current is None:
                rows[key] = EngagementVelocityDaily(
                    work_id=row.public_work_id,
                    category_id=row.category_id,
                    metric_date=metric_date,
                    views=0,
                    shares=0,
                    qr_scans=0,
                    favorites=1,
                )
            else:
                rows[key] = EngagementVelocityDaily(
                    work_id=current.work_id,
                    category_id=current.category_id,
                    metric_date=current.metric_date,
                    views=current.views,
                    shares=current.shares,
                    qr_scans=current.qr_scans,
                    favorites=current.favorites + 1,
                )
        return tuple(rows.values())

    async def add(self, draft: EngagementVelocitySnapshotDraft) -> bool:
        bind = self._session.get_bind()
        dialect_insert = (
            sqlite_insert if bind.dialect.name == "sqlite" else postgresql_insert
        )
        statement = dialect_insert(EngagementVelocitySnapshot).values(
            id=draft.id,
            window_start=draft.window_start,
            window_end=draft.window_end,
            formula_version=draft.formula_version,
            candidate_count=draft.candidate_count,
            total_score=draft.total_score,
            generated_at=draft.generated_at,
        )
        await self._session.execute(
            statement.on_conflict_do_nothing(
                index_elements=["window_start", "window_end"]
            )
        )
        await self._session.flush()
        persisted = await self._session.scalar(
            select(EngagementVelocitySnapshot).where(
                EngagementVelocitySnapshot.window_start == draft.window_start,
                EngagementVelocitySnapshot.window_end == draft.window_end,
            )
        )
        if persisted is None or persisted.id != draft.id:
            return False
        self._session.add_all(
            [
                EngagementVelocitySnapshotItem(
                    snapshot_id=draft.id,
                    public_work_id=item.work_id,
                    category_id=item.category_id,
                    score=item.score,
                    rank=item.rank,
                    display_order=item.display_order,
                )
                for item in draft.items
            ]
        )
        await self._session.flush()
        return True

    @staticmethod
    def _item_view(item: EngagementVelocitySnapshotItem) -> EngagementVelocityItem:
        return EngagementVelocityItem(
            work_id=item.public_work_id,
            category_id=item.category_id,
            score=Decimal(str(item.score)),
            rank=item.rank,
            display_order=item.display_order,
        )
