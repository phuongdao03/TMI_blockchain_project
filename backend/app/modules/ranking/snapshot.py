import hashlib
import json
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.modules.ranking.types import (
    RankingRun,
    RankingSnapshotDraft,
    RankingSnapshotItemDraft,
)


class RankingCalculatorPort(Protocol):
    async def calculate(self, campaign_id: UUID) -> RankingRun: ...


class RankingSnapshotRepositoryPort(Protocol):
    async def next_version(self, campaign_id: UUID) -> int: ...

    async def add(self, draft: RankingSnapshotDraft) -> None: ...

    async def commit(self) -> None: ...


class RankingAuditPort(Protocol):
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


def create_snapshot_draft(
    run: RankingRun,
    *,
    version: int,
    created_at: datetime,
    snapshot_id: UUID | None = None,
) -> RankingSnapshotDraft:
    if version <= 0:
        raise ValueError("snapshot version must be positive")
    normalized_created_at = (
        created_at.replace(tzinfo=UTC)
        if created_at.tzinfo is None
        else created_at.astimezone(UTC)
    )
    items = tuple(
        RankingSnapshotItemDraft(
            work_id=item.work_id,
            category_id=item.category_id,
            rank=item.rank,
            category_rank=item.category_rank,
            display_order=display_order,
            score=item.score,
            effective_vote_count=item.score,
        )
        for display_order, item in enumerate(run.calculation.items, start=1)
    )
    source_payload = {
        "campaignId": str(run.campaign.campaign_id),
        "campaignRuleVersion": run.campaign.rule_version,
        "formulaVersion": run.calculation.formula_version,
        "candidates": [
            {
                "workId": str(item.work_id),
                "categoryId": str(item.category_id),
                "effectiveVoteCount": item.effective_vote_count,
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
                "rank": item.rank,
                "categoryRank": item.category_rank,
                "displayOrder": item.display_order,
                "score": item.score,
            }
            for item in items
        ],
    }
    return RankingSnapshotDraft(
        id=snapshot_id or uuid4(),
        campaign_id=run.campaign.campaign_id,
        version=version,
        formula_version=run.calculation.formula_version,
        campaign_rule_version=run.campaign.rule_version,
        source_digest=_digest(source_payload),
        result_digest=_digest(result_payload),
        candidate_count=len(items),
        total_valid_votes=sum(item.effective_vote_count for item in items),
        created_at=normalized_created_at,
        items=items,
    )


class RankingSnapshotService:
    def __init__(
        self,
        calculator: RankingCalculatorPort,
        repository: RankingSnapshotRepositoryPort,
        *,
        audit: RankingAuditPort,
    ) -> None:
        self._calculator = calculator
        self._repository = repository
        self._audit = audit

    async def create(
        self,
        campaign_id: UUID,
        *,
        created_at: datetime | None = None,
        request_id: str | None = None,
    ) -> RankingSnapshotDraft:
        run = await self._calculator.calculate(campaign_id)
        version = await self._repository.next_version(campaign_id)
        return await self._persist(
            run,
            version=version,
            created_at=created_at,
            request_id=request_id,
            actor_user_id=None,
            action="ranking.snapshot.created",
        )

    async def recount(
        self,
        campaign_id: UUID,
        *,
        actor_user_id: UUID | None = None,
        created_at: datetime | None = None,
        request_id: str | None = None,
    ) -> RankingSnapshotDraft:
        run = await self._calculator.calculate(campaign_id)
        version = await self._repository.next_version(campaign_id)
        return await self._persist(
            run,
            version=version,
            created_at=created_at,
            request_id=request_id,
            actor_user_id=actor_user_id,
            action="ranking.snapshot.recounted",
        )

    async def create_initial(
        self,
        campaign_id: UUID,
        *,
        created_at: datetime | None = None,
        request_id: str | None = None,
    ) -> RankingSnapshotDraft | None:
        version = await self._repository.next_version(campaign_id)
        if version != 1:
            await self._repository.commit()
            return None
        run = await self._calculator.calculate(campaign_id)
        return await self._persist(
            run,
            version=version,
            created_at=created_at,
            request_id=request_id,
            actor_user_id=None,
            action="ranking.snapshot.created",
        )

    async def _persist(
        self,
        run: RankingRun,
        *,
        version: int,
        created_at: datetime | None,
        request_id: str | None,
        actor_user_id: UUID | None,
        action: str,
    ) -> RankingSnapshotDraft:
        draft = create_snapshot_draft(
            run,
            version=version,
            created_at=created_at or datetime.now(UTC),
        )
        await self._repository.add(draft)
        self._audit.record(
            actor_user_id=actor_user_id,
            action=action,
            resource_type="ranking_snapshot",
            resource_id=str(draft.id),
            after={
                "campaign_id": str(draft.campaign_id),
                "version": draft.version,
                "formula_version": draft.formula_version,
                "campaign_rule_version": draft.campaign_rule_version,
                "source_digest": draft.source_digest,
                "result_digest": draft.result_digest,
                "candidate_count": draft.candidate_count,
                "total_valid_votes": draft.total_valid_votes,
            },
            request_id=request_id,
        )
        await self._repository.commit()
        return draft
