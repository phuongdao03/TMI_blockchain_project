from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.media.models import MediaAsset


class MediaAssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, asset: MediaAsset) -> None:
        self._session.add(asset)

    async def get_by_id(
        self,
        media_id: UUID,
        *,
        for_update: bool = False,
    ) -> MediaAsset | None:
        statement = select(MediaAsset).where(MediaAsset.id == media_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(MediaAsset | None, await self._session.scalar(statement))
