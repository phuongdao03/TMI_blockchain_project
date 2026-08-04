from collections import Counter, defaultdict
from datetime import UTC, datetime
from math import ceil
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dossiers.models import Category
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkTag,
    PublicWorkVisibility,
)
from app.modules.search.discovery_models import (
    SearchAnalyticsSnapshot,
    SearchEvent,
    SearchSuppressedPhrase,
    SearchTrendingSnapshot,
)
from app.modules.search.discovery_types import (
    RelatedWork,
    SearchAnalyticsPoint,
    SearchAnalyticsSummary,
    TrendingSearch,
)


class SearchDiscoveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def add_event(self, event: SearchEvent) -> bool:
        existing = await self._session.scalar(
            select(SearchEvent.id).where(SearchEvent.request_id == event.request_id)
        )
        if existing is not None:
            return False
        try:
            async with self._session.begin_nested():
                self._session.add(event)
                await self._session.flush()
        except IntegrityError:
            return False
        return True

    async def record_click(self, request_id: str, work_id: UUID) -> bool:
        public_work = await self._session.scalar(
            select(PublicWork.id)
            .join(Category, Category.id == PublicWork.category_id)
            .where(
                PublicWork.id == work_id,
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.published_at.is_not(None),
                PublicWork.published_at <= datetime.now(UTC),
                PublicWork.deleted_at.is_(None),
                Category.is_active.is_(True),
            )
        )
        if public_work is None:
            return False
        result = await self._session.execute(
            update(SearchEvent)
            .where(
                SearchEvent.request_id == request_id,
                SearchEvent.selected_work_id.is_(None),
            )
            .values(selected_work_id=work_id)
        )
        return bool(getattr(result, "rowcount", 0))

    async def aggregate(
        self, *, start: datetime, end: datetime, period: str, minimum_count: int
    ) -> int:
        events = (
            (
                await self._session.execute(
                    select(SearchEvent).where(
                        SearchEvent.created_at >= start,
                        SearchEvent.created_at < end,
                        SearchEvent.normalized_query.is_not(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        suppressed = set(
            (
                await self._session.scalars(select(SearchSuppressedPhrase.query_hash))
            ).all()
        )
        await self._session.execute(
            delete(SearchTrendingSnapshot).where(
                SearchTrendingSnapshot.period == period,
                SearchTrendingSnapshot.period_start == start,
            )
        )
        counts = Counter(event.query_hash for event in events)
        labels = {event.query_hash: event.normalized_query for event in events}
        now = datetime.now(UTC)
        rows = [
            SearchTrendingSnapshot(
                period=period,
                period_start=start,
                query_hash=query_hash,
                display_query=labels[query_hash] or "",
                search_count=count,
                is_suppressed=query_hash in suppressed,
                generated_at=now,
            )
            for query_hash, count in counts.items()
            if count >= minimum_count
        ]
        self._session.add_all(rows)
        if period == "DAILY":
            await self._materialize_analytics(start=start, end=end, generated_at=now)
        await self._session.flush()
        return len(rows)

    async def _materialize_analytics(
        self, *, start: datetime, end: datetime, generated_at: datetime
    ) -> None:
        events = (
            (
                await self._session.execute(
                    select(SearchEvent).where(
                        SearchEvent.created_at >= start, SearchEvent.created_at < end
                    )
                )
            )
            .scalars()
            .all()
        )
        await self._session.execute(
            delete(SearchAnalyticsSnapshot).where(
                SearchAnalyticsSnapshot.period_start == start
            )
        )
        grouped: dict[str, list[SearchEvent]] = defaultdict(list)
        grouped[""].extend(events)
        for event in events:
            if event.category_slug:
                grouped[event.category_slug].append(event)
        for category, rows in grouped.items():
            durations = sorted(row.duration_ms for row in rows)
            p95 = durations[max(ceil(len(durations) * 0.95) - 1, 0)] if durations else 0
            self._session.add(
                SearchAnalyticsSnapshot(
                    period_start=start,
                    category_slug=category,
                    search_count=len(rows),
                    zero_result_count=sum(row.result_count == 0 for row in rows),
                    click_count=sum(row.selected_work_id is not None for row in rows),
                    latency_p95_ms=p95,
                    generated_at=generated_at,
                )
            )

    async def trending(self, *, period: str, limit: int) -> tuple[TrendingSearch, ...]:
        latest = await self._session.scalar(
            select(func.max(SearchTrendingSnapshot.period_start)).where(
                SearchTrendingSnapshot.period == period
            )
        )
        if latest is None:
            return ()
        rows = (
            await self._session.execute(
                select(SearchTrendingSnapshot)
                .where(
                    SearchTrendingSnapshot.period == period,
                    SearchTrendingSnapshot.period_start == latest,
                    SearchTrendingSnapshot.is_suppressed.is_(False),
                )
                .order_by(
                    SearchTrendingSnapshot.search_count.desc(),
                    SearchTrendingSnapshot.query_hash,
                )
                .limit(limit)
            )
        ).scalars()
        return tuple(
            TrendingSearch(row.query_hash, row.display_query, row.search_count)
            for row in rows
        )

    async def suppress(
        self, *, query_hash: str, actor_id: UUID, reason: str, suppressed: bool
    ) -> None:
        existing = await self._session.get(SearchSuppressedPhrase, query_hash)
        if suppressed and existing is None:
            self._session.add(
                SearchSuppressedPhrase(
                    query_hash=query_hash, suppressed_by_user_id=actor_id, reason=reason
                )
            )
        elif suppressed and existing is not None:
            existing.reason = reason
            existing.suppressed_by_user_id = actor_id
        elif existing is not None:
            await self._session.delete(existing)
        await self._session.execute(
            update(SearchTrendingSnapshot)
            .where(SearchTrendingSnapshot.query_hash == query_hash)
            .values(is_suppressed=suppressed)
        )

    async def related(
        self, *, slug: str, limit: int, now: datetime
    ) -> tuple[RelatedWork, ...]:
        source = await self._session.scalar(
            select(PublicWork).where(
                PublicWork.slug == slug,
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.deleted_at.is_(None),
                PublicWork.published_at <= now,
            )
        )
        if source is None:
            return ()
        source_tags = set(
            (
                await self._session.scalars(
                    select(PublicWorkTag.tag_id).where(
                        PublicWorkTag.public_work_id == source.id
                    )
                )
            ).all()
        )
        candidates = cast(
            list[tuple[PublicWork, Category]],
            list(
                (
                    await self._session.execute(
                        select(PublicWork, Category)
                        .join(Category, Category.id == PublicWork.category_id)
                        .where(
                            PublicWork.id != source.id,
                            PublicWork.publication_status
                            == PublicationStatus.PUBLISHED,
                            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                            PublicWork.deleted_at.is_(None),
                            PublicWork.published_at <= now,
                            Category.is_active.is_(True),
                        )
                        .order_by(PublicWork.published_at.desc(), PublicWork.id)
                        .limit(max(limit * 10, 40))
                    )
                ).all()
            ),
        )
        candidate_ids = [work.id for work, _ in candidates]
        tag_rows = (
            (
                await self._session.execute(
                    select(PublicWorkTag.public_work_id, PublicWorkTag.tag_id).where(
                        PublicWorkTag.public_work_id.in_(candidate_ids)
                    )
                )
            ).all()
            if candidate_ids
            else []
        )
        tags: dict[UUID, set[UUID]] = defaultdict(set)
        for work_id, tag_id in tag_rows:
            tags[work_id].add(tag_id)

        source_terms = set(
            f"{source.title} {source.short_description}".casefold().split()
        )

        def score(
            item: tuple[PublicWork, Category],
        ) -> tuple[int, int, int, datetime, str]:
            work, _ = item
            candidate_terms = set(
                f"{work.title} {work.short_description}".casefold().split()
            )
            return (
                int(work.category_id == source.category_id),
                len(source_tags & tags[work.id]),
                len(source_terms & candidate_terms),
                work.published_at or datetime.min.replace(tzinfo=UTC),
                str(work.id),
            )

        ranked = sorted(candidates, key=score, reverse=True)
        category_cap = max(1, ceil(limit * 0.75))
        selected: list[tuple[PublicWork, Category]] = []
        category_counts: Counter[UUID] = Counter()
        for item in ranked:
            if category_counts[item[0].category_id] >= category_cap:
                continue
            selected.append(item)
            category_counts[item[0].category_id] += 1
            if len(selected) == limit:
                break
        if len(selected) < limit:
            selected_ids = {item[0].id for item in selected}
            selected.extend(item for item in ranked if item[0].id not in selected_ids)
        ranked = selected[:limit]
        return tuple(
            RelatedWork(
                work.id,
                work.slug,
                work.title,
                work.short_description,
                category.name,
                category.slug or "",
                work.published_at,
            )
            for work, category in ranked
            if work.published_at is not None and category.slug is not None
        )

    async def analytics(
        self, *, start: datetime, end: datetime, category: str | None
    ) -> SearchAnalyticsSummary:
        rows = (
            (
                await self._session.execute(
                    select(SearchAnalyticsSnapshot)
                    .where(
                        SearchAnalyticsSnapshot.period_start >= start,
                        SearchAnalyticsSnapshot.period_start < end,
                        SearchAnalyticsSnapshot.category_slug == (category or ""),
                    )
                    .order_by(SearchAnalyticsSnapshot.period_start)
                )
            )
            .scalars()
            .all()
        )
        points = tuple(
            SearchAnalyticsPoint(
                row.period_start,
                row.category_slug or None,
                row.search_count,
                row.zero_result_count,
                row.click_count,
                row.latency_p95_ms,
            )
            for row in rows
        )
        total = sum(row.search_count for row in rows)
        weighted_p95 = (
            round(sum(row.latency_p95_ms * row.search_count for row in rows) / total)
            if total
            else 0
        )
        return SearchAnalyticsSummary(
            total,
            sum(row.zero_result_count for row in rows),
            sum(row.click_count for row in rows),
            weighted_p95,
            points,
        )
