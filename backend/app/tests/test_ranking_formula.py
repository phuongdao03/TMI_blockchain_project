from uuid import UUID

import pytest

from app.modules.ranking.formula import (
    RANKING_FORMULA_VERSION,
    RankingCandidate,
    calculate_rankings,
)

WORK_A = UUID("00000000-0000-0000-0000-000000000001")
WORK_B = UUID("00000000-0000-0000-0000-000000000002")
WORK_C = UUID("00000000-0000-0000-0000-000000000003")
CATEGORY_ID = UUID("00000000-0000-0000-0001-000000000001")


def test_calculate_rankings_orders_candidates_by_effective_votes() -> None:
    result = calculate_rankings(
        (
            RankingCandidate(WORK_A, CATEGORY_ID, 4),
            RankingCandidate(WORK_B, CATEGORY_ID, 9),
            RankingCandidate(WORK_C, CATEGORY_ID, 1),
        )
    )

    assert result.formula_version == RANKING_FORMULA_VERSION
    assert [item.work_id for item in result.items] == [WORK_B, WORK_A, WORK_C]
    assert [item.score for item in result.items] == [9, 4, 1]
    assert [item.rank for item in result.items] == [1, 2, 3]


def test_calculate_rankings_assigns_competition_rank_and_stable_tie_order() -> None:
    result = calculate_rankings(
        (
            RankingCandidate(WORK_C, CATEGORY_ID, 5),
            RankingCandidate(WORK_B, CATEGORY_ID, 2),
            RankingCandidate(WORK_A, CATEGORY_ID, 5),
        )
    )

    assert [item.work_id for item in result.items] == [WORK_A, WORK_C, WORK_B]
    assert [item.rank for item in result.items] == [1, 1, 3]


def test_calculate_rankings_keeps_zero_vote_candidates() -> None:
    result = calculate_rankings(
        (
            RankingCandidate(WORK_B, CATEGORY_ID, 0),
            RankingCandidate(WORK_A, CATEGORY_ID, 0),
        )
    )

    assert [item.work_id for item in result.items] == [WORK_A, WORK_B]
    assert [item.score for item in result.items] == [0, 0]
    assert [item.rank for item in result.items] == [1, 1]


def test_calculate_rankings_rejects_duplicate_candidates() -> None:
    with pytest.raises(ValueError, match="duplicate work_id"):
        calculate_rankings(
            (
                RankingCandidate(WORK_A, CATEGORY_ID, 1),
                RankingCandidate(WORK_A, CATEGORY_ID, 2),
            )
        )


def test_ranking_candidate_rejects_negative_effective_vote_count() -> None:
    with pytest.raises(ValueError, match="effective_vote_count"):
        RankingCandidate(WORK_A, CATEGORY_ID, -1)


def test_calculate_rankings_is_independent_of_input_order() -> None:
    candidates = (
        RankingCandidate(WORK_A, CATEGORY_ID, 3),
        RankingCandidate(WORK_B, CATEGORY_ID, 3),
        RankingCandidate(WORK_C, CATEGORY_ID, 1),
    )

    assert calculate_rankings(candidates) == calculate_rankings(
        tuple(reversed(candidates))
    )
