from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community.errors import CommunityNotFoundError
from app.modules.community.repository import CommunityRepository
from app.modules.media.errors import MediaInvalidStateError, MediaNotFoundError
from app.modules.media.types import COMMUNITY_POST_IMAGE_MAX_BYTES, MediaContentView


class CommunityImageReader(Protocol):
    async def download_community_post_image(
        self,
        media_id: UUID,
    ) -> MediaContentView: ...

    async def download_community_avatar(self, media_id: UUID) -> MediaContentView: ...


class CommunityMediaDeliveryService:
    def __init__(
        self,
        session: AsyncSession,
        media_reader: CommunityImageReader,
        *,
        image_max_bytes: int = COMMUNITY_POST_IMAGE_MAX_BYTES,
        avatar_max_bytes: int = 5_242_880,
    ) -> None:
        self._session = session
        self._repository = CommunityRepository(
            session,
            image_max_bytes=image_max_bytes,
            avatar_max_bytes=avatar_max_bytes,
        )
        self._media_reader = media_reader

    async def deliver(
        self,
        *,
        slug: str,
        media_id: UUID,
        viewer_user_id: UUID | None,
    ) -> MediaContentView:
        async with self._session.begin():
            asset = await self._repository.get_deliverable_community_image(
                slug=slug,
                media_id=media_id,
                viewer_user_id=viewer_user_id,
            )
            if asset is None:
                raise CommunityNotFoundError()
        try:
            image = await self._media_reader.download_community_post_image(media_id)
        except (MediaInvalidStateError, MediaNotFoundError):
            raise CommunityNotFoundError() from None
        async with self._session.begin():
            asset = await self._repository.get_deliverable_community_image(
                slug=slug,
                media_id=media_id,
                viewer_user_id=viewer_user_id,
            )
            if asset is None:
                raise CommunityNotFoundError()
        return image

    async def deliver_avatar(self, media_id: UUID) -> MediaContentView:
        async with self._session.begin():
            asset = await self._repository.get_deliverable_community_avatar(media_id)
            if asset is None:
                raise CommunityNotFoundError()
        try:
            image = await self._media_reader.download_community_avatar(media_id)
        except (MediaInvalidStateError, MediaNotFoundError):
            raise CommunityNotFoundError() from None
        async with self._session.begin():
            asset = await self._repository.get_deliverable_community_avatar(media_id)
            if asset is None:
                raise CommunityNotFoundError()
        return image
