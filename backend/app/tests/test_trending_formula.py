from uuid import UUID

from app.modules.ranking.trending_formula import (
    TRENDING_FORMULA_VERSION,
    TrendingCandidate,
    calculate_trending,
)

CATEGORY_ID = UUID("51000000-0000-0000-0000-000000000001")
WORK_A = UUID("52000000-0000-0000-0000-000000000001")
WORK_B = UUID("52000000-0000-0000-0000-000000000002")
WORK_C = UUID("52000000-0000-0000-0000-000000000003")


def test_calculate_trending_orders_scores_with_standard_competition_rank() -> None:
    result = calculate_trending(
        (
            TrendingCandidate(WORK_C, CATEGORY_ID, 0),
            TrendingCandidate(WORK_B, CATEGORY_ID, 5),
            TrendingCandidate(WORK_A, CATEGORY_ID, 5),
        )
    )

    assert result.formula_version == TRENDING_FORMULA_VERSION
    assert [item.work_id for item in result.items] == [WORK_A, WORK_B, WORK_C]
    assert [item.score for item in result.items] == [5, 5, 0]
    assert [item.rank for item in result.items] == [1, 1, 3]
    assert [item.display_order for item in result.items] == [1, 2, 3]


def test_trending_candidate_rejects_negative_score() -> None:
    try:
        TrendingCandidate(WORK_A, CATEGORY_ID, -1)
    except ValueError as error:
        assert "score" in str(error)
    else:
        raise AssertionError("negative trending score must be rejected")
