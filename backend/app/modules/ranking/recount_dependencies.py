from typing import Annotated

from fastapi import Depends

from app.modules.ranking.recount import RankingRecountService


def get_ranking_recount_service() -> RankingRecountService:
    from app.workers.ranking_tasks import recount_ranking_snapshot

    return RankingRecountService(
        enqueue=lambda campaign_id, actor_user_id, request_id: (
            recount_ranking_snapshot.delay(
                str(campaign_id),
                actor_user_id=str(actor_user_id),
                request_id=request_id,
            )
        )
    )


RankingRecountServiceDependency = Annotated[
    RankingRecountService,
    Depends(get_ranking_recount_service),
]
