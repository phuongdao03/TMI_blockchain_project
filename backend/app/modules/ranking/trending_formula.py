from dataclasses import dataclass
from uuid import UUID

TRENDING_FORMULA_VERSION = "vote-velocity-v1"


@dataclass(frozen=True, slots=True)
class TrendingCandidate:
    work_id: UUID
    category_id: UUID
    score: int

    def __post_init__(self) -> None:
        if self.score < 0:
            raise ValueError("score must be non-negative")


@dataclass(frozen=True, slots=True)
class TrendingItem:
    work_id: UUID
    category_id: UUID
    score: int
    rank: int
    display_order: int


@dataclass(frozen=True, slots=True)
class TrendingCalculation:
    formula_version: str
    items: tuple[TrendingItem, ...]


def calculate_trending(
    candidates: tuple[TrendingCandidate, ...],
) -> TrendingCalculation:
    work_ids = [candidate.work_id for candidate in candidates]
    if len(work_ids) != len(set(work_ids)):
        raise ValueError("duplicate work_id in trending candidates")

    ordered = sorted(
        candidates,
        key=lambda candidate: (-candidate.score, candidate.work_id.int),
    )
    items: list[TrendingItem] = []
    previous_score: int | None = None
    current_rank = 0
    for display_order, candidate in enumerate(ordered, start=1):
        if candidate.score != previous_score:
            current_rank = display_order
            previous_score = candidate.score
        items.append(
            TrendingItem(
                work_id=candidate.work_id,
                category_id=candidate.category_id,
                score=candidate.score,
                rank=current_rank,
                display_order=display_order,
            )
        )
    return TrendingCalculation(
        formula_version=TRENDING_FORMULA_VERSION,
        items=tuple(items),
    )
