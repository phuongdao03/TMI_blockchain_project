from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.modules.engagement.velocity_types import (
    EngagementVelocityCalculation,
    EngagementVelocityDaily,
    EngagementVelocityItem,
)

VELOCITY_FORMULA_VERSION = "engagement-velocity-v1"
DECAY_FACTOR = Decimal("0.82")
VELOCITY_WINDOW_DAYS = 7
SCORE_QUANTUM = Decimal("0.00000001")


def calculate_velocity(
    rows: tuple[EngagementVelocityDaily, ...],
    *,
    as_of_date: date,
) -> EngagementVelocityCalculation:
    scores: dict[UUID, tuple[UUID, Decimal]] = {}
    for row in rows:
        days_ago = (as_of_date - row.metric_date).days
        if days_ago < 0 or days_ago >= VELOCITY_WINDOW_DAYS:
            continue
        if min(row.views, row.shares, row.qr_scans, row.favorites) < 0:
            raise ValueError("engagement counts must be non-negative")
        base_score = row.views + (3 * row.shares) + (4 * row.qr_scans) + (
            2 * row.favorites
        )
        weighted_score = (Decimal(base_score) * (DECAY_FACTOR**days_ago)).quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        current = scores.get(row.work_id)
        if current is None:
            scores[row.work_id] = (row.category_id, weighted_score)
        else:
            category_id, score = current
            if category_id != row.category_id:
                raise ValueError("a work cannot belong to multiple categories")
            scores[row.work_id] = (category_id, score + weighted_score)

    ordered = sorted(
        scores.items(),
        key=lambda entry: (-entry[1][1], entry[0].int),
    )
    items: list[EngagementVelocityItem] = []
    previous_score: Decimal | None = None
    current_rank = 0
    for display_order, (work_id, (category_id, score)) in enumerate(ordered, start=1):
        normalized_score = score.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
        if normalized_score != previous_score:
            current_rank = display_order
            previous_score = normalized_score
        items.append(
            EngagementVelocityItem(
                work_id=work_id,
                category_id=category_id,
                score=normalized_score,
                rank=current_rank,
                display_order=display_order,
            )
        )
    return EngagementVelocityCalculation(
        formula_version=VELOCITY_FORMULA_VERSION,
        items=tuple(items),
        total_score=sum((item.score for item in items), Decimal("0")).quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        ),
    )
