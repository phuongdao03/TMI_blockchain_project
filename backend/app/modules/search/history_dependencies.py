from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.search.history_service import SearchHistoryService


def get_search_history_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> SearchHistoryService:
    return SearchHistoryService(
        session,
        retention_days=settings.search_history_retention_days,
        list_limit=settings.search_history_list_limit,
    )


SearchHistoryServiceDependency = Annotated[
    SearchHistoryService,
    Depends(get_search_history_service),
]
