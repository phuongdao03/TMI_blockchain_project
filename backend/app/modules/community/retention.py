from uuid import uuid4

from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.models import CommunityPostMedia, CommunityProfile
from app.modules.community.service import CommunityMediaAssetDeleter
from app.modules.media.errors import MediaNotFoundError
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.types import MediaPurpose
from app.modules.users.models import UserProfile


class CommunityMediaRetentionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def purge_deleted_assets(
        self,
        media_asset_deleter: CommunityMediaAssetDeleter,
        *,
        limit: int = 500,
    ) -> int:
        async with self._session.begin():
            assets = await self._session.execute(
                select(MediaAsset.id, MediaAsset.owner_user_id)
                .where(
                    MediaAsset.purpose == MediaPurpose.COMMUNITY_POST.value,
                    MediaAsset.status == MediaStatus.DELETED,
                    ~exists(
                        select(CommunityPostMedia.media_asset_id).where(
                            CommunityPostMedia.media_asset_id == MediaAsset.id
                        )
                    ),
                    ~exists(
                        select(CommunityProfile.avatar_media_id).where(
                            CommunityProfile.avatar_media_id == MediaAsset.id
                        )
                    ),
                    ~exists(
                        select(UserProfile.avatar_media_id).where(
                            UserProfile.avatar_media_id == MediaAsset.id
                        )
                    ),
                )
                .order_by(MediaAsset.deleted_at, MediaAsset.id)
                .limit(limit)
            )
            candidates = tuple(assets.all())
        deleted = 0
        for asset_id, owner_user_id in candidates:
            principal = AuthPrincipal(
                user_id=owner_user_id,
                session_id=uuid4(),
                email="community-retention@system.invalid",
                roles=(),
            )
            try:
                await media_asset_deleter.delete_community_post_asset(
                    principal,
                    asset_id,
                    owner_user_id=owner_user_id,
                )
            except MediaNotFoundError:
                continue
            try:
                async with self._session.begin():
                    async with self._session.begin_nested():
                        result = await self._session.execute(
                            delete(MediaAsset).where(
                                MediaAsset.id == asset_id,
                                MediaAsset.purpose == MediaPurpose.COMMUNITY_POST.value,
                                MediaAsset.status == MediaStatus.DELETED,
                            )
                        )
                        await self._session.flush()
                        removed = int(getattr(result, "rowcount", 0) or 0)
                deleted += removed
            except IntegrityError:
                # Keep metadata when another feature still references the asset.
                continue
        return deleted
