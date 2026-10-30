from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.supplements.models import SupplementRequest


class SupplementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self, dossier_id: UUID, *, include_open: bool
    ) -> tuple[SupplementRequest, ...]:
        query = select(SupplementRequest).where(
            SupplementRequest.dossier_id == dossier_id
        )
        if not include_open:
            query = query.where(SupplementRequest.status != "OPEN")
        return tuple(
            await self.session.scalars(
                query.options(selectinload(SupplementRequest.responses))
                .order_by(SupplementRequest.created_at, SupplementRequest.id)
                .limit(100)
            )
        )

    async def get(self, dossier_id: UUID, request_id: UUID) -> SupplementRequest | None:
        return cast(
            SupplementRequest | None,
            await self.session.scalar(
                select(SupplementRequest)
                .where(
                    SupplementRequest.id == request_id,
                    SupplementRequest.dossier_id == dossier_id,
                )
                .options(selectinload(SupplementRequest.responses))
                .with_for_update()
            ),
        )

    async def count(self, dossier_id: UUID, *, states: tuple[str, ...]) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(SupplementRequest)
                .where(
                    SupplementRequest.dossier_id == dossier_id,
                    SupplementRequest.status.in_(states),
                )
            )
            or 0
        )
