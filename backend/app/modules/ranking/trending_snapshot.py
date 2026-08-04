import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from app.modules.ranking.trending_models import TrendingSnapshot
from app.modules.ranking.trending_service import floor_to_hour
from app.modules.ranking.trending_types import (
    TrendingRun,
    TrendingSnapshotDraft,
    TrendingSnapshotItemDraft,
)


class TrendingCalculatorPort(Protocol):
    async def calculate(self, *, window_end: datetime) -> TrendingRun: ...


class TrendingSnapshotRepositoryPort(Protocol):
    async def get_by_window(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> TrendingSnapshot | None: ...

    async def add(self, draft: TrendingSnapshotDraft) -> bool: ...

    async def commit(self) -> None: ...


class TrendingAuditPort(Protocol):
    def record(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        request_id: str | None = None,
    ) -> object: ...


def _digest(payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def create_trending_snapshot_draft(
    run: TrendingRun,
    *,
    created_at: datetime,
    snapshot_id: UUID | None = None,
) -> TrendingSnapshotDraft:
    normalized_created_at = (
        created_at.replace(tzinfo=UTC)
        if created_at.tzinfo is None
        else created_at.astimezone(UTC)
    )
    items = tuple(
        TrendingSnapshotItemDraft(
            work_id=item.work_id,
            category_id=item.category_id,
            rank=item.rank,
            display_order=item.display_order,
            score=item.score,
        )
        for item in run.calculation.items
    )
    source_payload = {
        "windowStart": run.window.window_start.isoformat(),
        "windowEnd": run.window.window_end.isoformat(),
        "formulaVersion": run.calculation.formula_version,
        "candidates": [
            {
                "workId": str(item.work_id),
                "categoryId": str(item.category_id),
                "score": item.score,
            }
            for item in items
        ],
    }
    result_payload = {
        "formulaVersion": run.calculation.formula_version,
        "items": [
            {
                "workId": str(item.work_id),
                "categoryId": str(item.category_id),
                "score": item.score,
                "rank": item.rank,
                "displayOrder": item.display_order,
            }
            for item in items
        ],
    }
    return TrendingSnapshotDraft(
        id=snapshot_id or uuid4(),
        window_start=run.window.window_start,
        window_end=run.window.window_end,
        formula_version=run.calculation.formula_version,
        source_digest=_digest(source_payload),
        result_digest=_digest(result_payload),
        candidate_count=len(items),
        total_score=sum(item.score for item in items),
        created_at=normalized_created_at,
        items=items,
    )


class TrendingSnapshotService:
    def __init__(
        self,
        calculator: TrendingCalculatorPort,
        repository: TrendingSnapshotRepositoryPort,
        *,
        audit: TrendingAuditPort,
    ) -> None:
        self._calculator = calculator
        self._repository = repository
        self._audit = audit

    async def create(
        self,
        *,
        window_end: datetime,
        created_at: datetime | None = None,
        request_id: str | None = None,
    ) -> TrendingSnapshotDraft | None:
        normalized_end = floor_to_hour(window_end)
        normalized_start = normalized_end - timedelta(days=7)
        existing = await self._repository.get_by_window(
            window_start=normalized_start,
            window_end=normalized_end,
        )
        if existing is not None:
            await self._repository.commit()
            return None
        run = await self._calculator.calculate(window_end=normalized_end)
        draft = create_trending_snapshot_draft(
            run,
            created_at=created_at or datetime.now(UTC),
        )
        created = await self._repository.add(draft)
        if not created:
            await self._repository.commit()
            return None
        self._audit.record(
            actor_user_id=None,
            action="ranking.trending.snapshot.created",
            resource_type="trending_snapshot",
            resource_id=str(draft.id),
            after={
                "window_start": draft.window_start.isoformat(),
                "window_end": draft.window_end.isoformat(),
                "formula_version": draft.formula_version,
                "source_digest": draft.source_digest,
                "result_digest": draft.result_digest,
                "candidate_count": draft.candidate_count,
                "total_score": draft.total_score,
            },
            request_id=request_id,
        )
        await self._repository.commit()
        return draft
