from uuid import UUID

from app.modules.ranking.formula import RankingCandidate, calculate_rankings

CATEGORY_A = UUID("10000000-0000-0000-0000-000000000001")
CATEGORY_B = UUID("10000000-0000-0000-0000-000000000002")
WORK_A = UUID("20000000-0000-0000-0000-000000000001")
WORK_B = UUID("20000000-0000-0000-0000-000000000002")
WORK_C = UUID("20000000-0000-0000-0000-000000000003")
WORK_D = UUID("20000000-0000-0000-0000-000000000004")
WORK_E = UUID("20000000-0000-0000-0000-000000000005")


def test_calculate_rankings_assigns_competition_rank_per_category() -> None:
    result = calculate_rankings(
        (
            RankingCandidate(WORK_E, CATEGORY_B, 0),
            RankingCandidate(WORK_C, CATEGORY_A, 8),
            RankingCandidate(WORK_A, CATEGORY_A, 10),
            RankingCandidate(WORK_D, CATEGORY_A, 8),
            RankingCandidate(WORK_B, CATEGORY_B, 9),
        )
    )

    assert [item.work_id for item in result.items] == [
        WORK_A,
        WORK_B,
        WORK_C,
        WORK_D,
        WORK_E,
    ]
    assert [item.rank for item in result.items] == [1, 2, 3, 3, 5]
    assert [item.category_rank for item in result.items] == [1, 1, 2, 2, 2]
    assert [item.category_id for item in result.items] == [
        CATEGORY_A,
        CATEGORY_B,
        CATEGORY_A,
        CATEGORY_A,
        CATEGORY_B,
    ]
