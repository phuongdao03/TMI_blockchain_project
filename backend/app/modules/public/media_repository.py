from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.media.models import MediaAsset
from app.modules.public.models import PublicWork, PublicWorkMedia


class PublicMediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_work(
        self, work_id: UUID, *, for_update: bool = False
    ) -> PublicWork | None:
        statement = select(PublicWork).where(PublicWork.id == work_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(PublicWork | None, await self._session.scalar(statement))

    async def get_asset(self, media_id: UUID) -> MediaAsset | None:
        return cast(
            MediaAsset | None,
            await self._session.scalar(
                select(MediaAsset).where(MediaAsset.id == media_id)
            ),
        )

    async def get_relation(
        self, relation_id: UUID, *, for_update: bool = False
    ) -> PublicWorkMedia | None:
        statement = select(PublicWorkMedia).where(PublicWorkMedia.id == relation_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(PublicWorkMedia | None, await self._session.scalar(statement))

    async def get_relation_with_asset(
        self, relation_id: UUID, *, for_update: bool = False
    ) -> tuple[PublicWorkMedia, MediaAsset] | None:
        statement = (
            select(PublicWorkMedia, MediaAsset)
            .join(MediaAsset, MediaAsset.id == PublicWorkMedia.media_asset_id)
            .where(PublicWorkMedia.id == relation_id)
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        row = (await self._session.execute(statement)).one_or_none()
        return cast(tuple[PublicWorkMedia, MediaAsset] | None, row)

    async def list_for_work(self, work_id: UUID) -> tuple[PublicWorkMedia, ...]:
        rows = await self._session.scalars(
            select(PublicWorkMedia)
            .where(PublicWorkMedia.public_work_id == work_id)
            .order_by(
                PublicWorkMedia.sort_order,
                PublicWorkMedia.created_at,
                PublicWorkMedia.id,
            )
        )
        return tuple(rows)

    def add(self, relation: PublicWorkMedia) -> None:
        self._session.add(relation)

    async def delete(self, relation: PublicWorkMedia) -> None:
        await self._session.delete(relation)
