from typing import cast
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.media.models import (
    MediaAsset,
    MediaConfidentiality,
    MediaEncryptionStatus,
    MediaStatus,
)
from app.modules.media.provenance import CURRENT_INSPECTION_POLICY_VERSION


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

    async def list_untrusted_active_ids(self, *, limit: int) -> tuple[UUID, ...]:
        rows = await self._session.scalars(
            select(MediaAsset.id)
            .where(
                MediaAsset.status == MediaStatus.ACTIVE,
                MediaAsset.deleted_at.is_(None),
                or_(
                    MediaAsset.hash_algorithm != "SHA-256",
                    MediaAsset.hash_algorithm.is_(None),
                    MediaAsset.hash_byte_length != MediaAsset.bytes,
                    MediaAsset.hash_byte_length.is_(None),
                    MediaAsset.inspection_policy_version
                    != CURRENT_INSPECTION_POLICY_VERSION,
                    MediaAsset.inspection_policy_version.is_(None),
                    (
                        (
                            MediaAsset.encryption_status
                            == MediaEncryptionStatus.ENCRYPTED
                        )
                        & (
                            MediaAsset.hash_storage_version
                            != MediaAsset.encrypted_object_version
                        )
                    ),
                    (
                        (
                            MediaAsset.encryption_status
                            != MediaEncryptionStatus.ENCRYPTED
                        )
                        & (
                            MediaAsset.hash_storage_version
                            != MediaAsset.cloudinary_version
                        )
                    ),
                    MediaAsset.hash_storage_version.is_(None),
                    MediaAsset.hash_computed_at.is_(None),
                ),
            )
            .order_by(MediaAsset.created_at, MediaAsset.id)
            .limit(limit)
        )
        return tuple(rows.all())

    async def list_legacy_private_ids(self, *, limit: int) -> tuple[UUID, ...]:
        rows = await self._session.scalars(
            select(MediaAsset.id)
            .where(
                MediaAsset.confidentiality == MediaConfidentiality.PRIVATE,
                MediaAsset.encryption_status
                == MediaEncryptionStatus.LEGACY_UNENCRYPTED,
                MediaAsset.status == MediaStatus.QUARANTINED,
                MediaAsset.deleted_at.is_(None),
            )
            .order_by(MediaAsset.created_at, MediaAsset.id)
            .limit(limit)
        )
        return tuple(rows.all())
