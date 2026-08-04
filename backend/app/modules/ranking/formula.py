from dataclasses import dataclass
from uuid import UUID

RANKING_FORMULA_VERSION = "effective-votes-v1"


@dataclass(frozen=True, slots=True)
class RankingCandidate:
    work_id: UUID
    category_id: UUID
    effective_vote_count: int

    def __post_init__(self) -> None:
        if self.effective_vote_count < 0:
            raise ValueError("effective_vote_count must be non-negative")


@dataclass(frozen=True, slots=True)
class RankingItem:
    work_id: UUID
    category_id: UUID
    score: int
    rank: int
    category_rank: int


@dataclass(frozen=True, slots=True)
class RankingCalculation:
    formula_version: str
    items: tuple[RankingItem, ...]


def calculate_rankings(
    candidates: tuple[RankingCandidate, ...],
) -> RankingCalculation:
    """Rank effective vote counts with deterministic competition ranking."""
    work_ids = [candidate.work_id for candidate in candidates]
    if len(work_ids) != len(set(work_ids)):
        raise ValueError("duplicate work_id in ranking candidates")

    ordered = sorted(
        candidates,
        key=lambda candidate: (
            -candidate.effective_vote_count,
            candidate.work_id.int,
        ),
    )
    items: list[RankingItem] = []
    previous_score: int | None = None
    current_rank = 0
    category_positions: dict[UUID, int] = {}
    category_previous_scores: dict[UUID, int] = {}
    category_ranks: dict[UUID, int] = {}
    for position, candidate in enumerate(ordered, start=1):
        if candidate.effective_vote_count != previous_score:
            current_rank = position
            previous_score = candidate.effective_vote_count
        category_position = category_positions.get(candidate.category_id, 0) + 1
        category_positions[candidate.category_id] = category_position
        if (
            category_previous_scores.get(candidate.category_id)
            != candidate.effective_vote_count
        ):
            category_ranks[candidate.category_id] = category_position
            category_previous_scores[candidate.category_id] = (
                candidate.effective_vote_count
            )
        items.append(
            RankingItem(
                work_id=candidate.work_id,
                category_id=candidate.category_id,
                score=candidate.effective_vote_count,
                rank=current_rank,
                category_rank=category_ranks[candidate.category_id],
            )
        )
    return RankingCalculation(
        formula_version=RANKING_FORMULA_VERSION,
        items=tuple(items),
    )
