from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency
from app.modules.engagement.activity_service import ActivityService
from app.modules.engagement.favorite_service import FavoriteService


async def get_favorite_service(
    session: SessionDependency,
) -> AsyncIterator[FavoriteService]:
    yield FavoriteService(session, audit=AuditService(session))


FavoriteServiceDependency = Annotated[
    FavoriteService,
    Depends(get_favorite_service),
]


async def get_activity_service(
    session: SessionDependency,
) -> AsyncIterator[ActivityService]:
    yield ActivityService(session)


ActivityServiceDependency = Annotated[
    ActivityService,
    Depends(get_activity_service),
]
