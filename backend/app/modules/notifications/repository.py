from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationDelivery,
)


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, notification: Notification) -> None:
        self._session.add(notification)

    def add_delivery(self, delivery: NotificationDelivery) -> None:
        self._session.add(delivery)

    async def by_event(self, user_id: UUID, event_id: UUID) -> Notification | None:
        return cast(
            Notification | None,
            await self._session.scalar(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.source_event_id == event_id,
                )
            ),
        )

    async def get_owned(
        self, user_id: UUID, notification_id: UUID, *, for_update: bool = False
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.user_id == user_id, Notification.id == notification_id
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(Notification | None, await self._session.scalar(statement))

    async def unread_count(self, user_id: UUID) -> int:
        return int(
            (
                await self._session.scalar(
                    select(func.count())
                    .select_from(Notification)
                    .where(
                        Notification.user_id == user_id, Notification.read_at.is_(None)
                    )
                )
            )
            or 0
        )

    async def list(
        self, user_id: UUID, *, page: int, page_size: int, unread_only: bool = False
    ) -> tuple[tuple[Notification, ...], int]:
        filters = [Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.read_at.is_(None))
        rows = tuple(
            (
                await self._session.scalars(
                    select(Notification)
                    .where(*filters)
                    .order_by(Notification.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        total = int(
            (
                await self._session.scalar(
                    select(func.count()).select_from(Notification).where(*filters)
                )
            )
            or 0
        )
        return rows, total

    async def mark_all_read(self, user_id: UUID, *, read_at: datetime) -> int:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
                .values(read_at=read_at)
            ),
        )
        return int(result.rowcount or 0)

    async def get_delivery(
        self,
        notification_id: UUID,
        channel: NotificationChannel,
        *,
        for_update: bool = False,
    ) -> NotificationDelivery | None:
        statement = select(NotificationDelivery).where(
            NotificationDelivery.notification_id == notification_id,
            NotificationDelivery.channel == channel,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(
            NotificationDelivery | None,
            await self._session.scalar(statement),
        )

    async def notification_with_email(
        self, notification_id: UUID
    ) -> tuple[Notification, str] | None:
        row = (
            await self._session.execute(
                select(Notification, User.email)
                .join(User, User.id == Notification.user_id)
                .where(Notification.id == notification_id)
            )
        ).one_or_none()
        return (row[0], row[1]) if row is not None else None
