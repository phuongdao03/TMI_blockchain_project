from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency
from app.modules.notifications.service import NotificationService


def get_notification_service(session: SessionDependency) -> NotificationService:
    return NotificationService(session)


NotificationServiceDependency = Annotated[
    NotificationService, Depends(get_notification_service)
]
