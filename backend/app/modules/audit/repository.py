from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, row: AuditLog) -> None:
        self._session.add(row)

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        actor_user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        include_access_events: bool = True,
    ) -> tuple[tuple[AuditLog, ...], int]:
        filters = []
        if actor_user_id is not None:
            filters.append(AuditLog.actor_user_id == actor_user_id)
        if action is not None:
            filters.append(AuditLog.action == action)
        if resource_type is not None:
            filters.append(AuditLog.resource_type == resource_type)
        if created_from is not None:
            filters.append(AuditLog.created_at >= created_from)
        if created_to is not None:
            filters.append(AuditLog.created_at <= created_to)
        if not include_access_events:
            filters.append(AuditLog.action != "audit.read")
        statement = (
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total_statement = select(func.count()).select_from(AuditLog).where(*filters)
        rows = tuple((await self._session.scalars(statement)).all())
        total = int((await self._session.scalar(total_statement)) or 0)
        return rows, total
