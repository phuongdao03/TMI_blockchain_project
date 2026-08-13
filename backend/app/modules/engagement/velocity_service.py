import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.velocity_formula import calculate_velocity
from app.modules.engagement.velocity_repository import EngagementVelocityRepository
from app.modules.engagement.velocity_types import (
    EngagementVelocityDaily,
    EngagementVelocitySnapshotDraft,
    EngagementVelocitySnapshotView,
)

logger = logging.getLogger(__name__)
VELOCITY_SNAPSHOT_GRACE = timedelta(minutes=10)


class EngagementVelocityRepositoryPort(Protocol):
    async def get_by_window(
        self,
        *,
        window_start: date,
        window_end: date,
    ) -> EngagementVelocitySnapshotView | None: ...

    async def list_daily_candidates(
        self,
        *,
        window_start: date,
        window_end: date,
    ) -> tuple[EngagementVelocityDaily, ...]: ...

    async def add(self, draft: EngagementVelocitySnapshotDraft) -> bool: ...


class EngagementVelocityAuditPort(Protocol):
    def record(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        after: dict[str, object] | None = None,
        request_id: str | None = None,
    ) -> object: ...


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def eligible_velocity_date(*, now: datetime) -> date | None:
    normalized = _as_utc(now)
    candidate = normalized.date() - timedelta(days=1)
    eligible_at = (
        datetime.combine(candidate + timedelta(days=1), time.min, tzinfo=UTC)
        + VELOCITY_SNAPSHOT_GRACE
    )
    return candidate if normalized >= eligible_at else None


class EngagementVelocityService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repository: EngagementVelocityRepositoryPort | None = None,
        audit: EngagementVelocityAuditPort,
    ) -> None:
        self._session = session
        self._repository = repository or EngagementVelocityRepository(session)
        self._audit = audit

    async def create(
        self,
        *,
        now: datetime,
        as_of_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> EngagementVelocitySnapshotView | None:
        normalized_now = _as_utc(now)
        window_end = as_of_date or eligible_velocity_date(now=normalized_now)
        if window_end is None:
            return None
        eligible_at = (
            datetime.combine(window_end + timedelta(days=1), time.min, tzinfo=UTC)
            + VELOCITY_SNAPSHOT_GRACE
        )
        if normalized_now < eligible_at:
            return None
        window_start = window_end - timedelta(days=6)
        async with self._session.begin():
            existing = await self._repository.get_by_window(
                window_start=window_start,
                window_end=window_end,
            )
            if existing is not None:
                return existing
            rows = await self._repository.list_daily_candidates(
                window_start=window_start,
                window_end=window_end,
            )
            calculation = calculate_velocity(
                tuple(rows),
                as_of_date=window_end,
            )
            draft = EngagementVelocitySnapshotDraft(
                id=uuid4(),
                window_start=window_start,
                window_end=window_end,
                formula_version=calculation.formula_version,
                candidate_count=len(calculation.items),
                total_score=calculation.total_score,
                generated_at=_as_utc(generated_at or normalized_now),
                items=calculation.items,
            )
            if not await self._repository.add(draft):
                return await self._repository.get_by_window(
                    window_start=window_start,
                    window_end=window_end,
                )
            self._audit.record(
                actor_user_id=None,
                action="engagement.velocity.snapshot.created",
                resource_type="engagement_velocity_snapshot",
                resource_id=window_end.isoformat(),
                after={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "formula_version": calculation.formula_version,
                    "candidate_count": len(calculation.items),
                    "total_score": str(calculation.total_score),
                },
                request_id=f"engagement-velocity:{window_end.isoformat()}",
            )
            logger.info(
                "engagement_velocity_snapshot_created",
                extra={
                    "action": "engagement.velocity.snapshot.created",
                    "window_end": window_end.isoformat(),
                    "candidate_count": len(calculation.items),
                    "outcome": "created",
                },
            )
            return await self._repository.get_by_window(
                window_start=window_start,
                window_end=window_end,
            )
