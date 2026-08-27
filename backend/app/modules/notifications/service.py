from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = NotificationRepository(session)

    async def consume(
        self,
        *,
        event_id: UUID,
        user_id: UUID,
        event_type: str,
        title: str,
        body: str,
        data: dict[str, object],
    ) -> Notification:
        try:
            async with self._session.begin():
                existing = await self._repository.by_event(user_id, event_id)
                if existing is not None:
                    return existing
                notification = Notification(
                    user_id=user_id,
                    source_event_id=event_id,
                    type=event_type,
                    title=title,
                    body=body,
                    data_json=data,
                    created_at=datetime.now(UTC),
                )
                self._repository.add(notification)
                await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            async with self._session.begin():
                existing = await self._repository.by_event(user_id, event_id)
            if existing is None:
                raise
            return existing
        return notification

    async def unread_count(self, user_id: UUID) -> int:
        async with self._session.begin():
            return await self._repository.unread_count(user_id)

    async def list(
        self,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
        unread_only: bool = False,
    ) -> tuple[tuple[Notification, ...], int]:
        async with self._session.begin():
            return await self._repository.list(
                user_id,
                page=page,
                page_size=page_size,
                unread_only=unread_only,
            )

    async def mark_read(
        self, *, user_id: UUID, notification_id: UUID
    ) -> Notification | None:
        async with self._session.begin():
            row = await self._repository.get_owned(
                user_id, notification_id, for_update=True
            )
            if row is not None and row.read_at is None:
                row.read_at = datetime.now(UTC)
            return row

    async def mark_all_read(self, user_id: UUID) -> int:
        async with self._session.begin():
            return await self._repository.mark_all_read(
                user_id, read_at=datetime.now(UTC)
            )
