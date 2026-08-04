from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.ranking.formula import RankingCalculation
from app.modules.voting.models import CampaignStatus

CLOSED_RANKING_CAMPAIGN_STATUSES = frozenset(
    {
        CampaignStatus.ENDED,
        CampaignStatus.RESULT_PENDING,
        CampaignStatus.PUBLISHED,
    }
)


@dataclass(frozen=True, slots=True)
class RankingCampaignSource:
    campaign_id: UUID
    status: CampaignStatus
    rule_version: int
    end_at: datetime


@dataclass(frozen=True, slots=True)
class RankingRun:
    campaign: RankingCampaignSource
    calculation: RankingCalculation


@dataclass(frozen=True, slots=True)
class RankingSnapshotItemDraft:
    work_id: UUID
    category_id: UUID
    rank: int
    category_rank: int
    display_order: int
    score: int
    effective_vote_count: int


@dataclass(frozen=True, slots=True)
class RankingSnapshotDraft:
    id: UUID
    campaign_id: UUID
    version: int
    formula_version: str
    campaign_rule_version: int
    source_digest: str
    result_digest: str
    candidate_count: int
    total_valid_votes: int
    created_at: datetime
    items: tuple[RankingSnapshotItemDraft, ...]
