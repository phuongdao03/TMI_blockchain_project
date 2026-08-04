import asyncio
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.media.models import MediaAsset, MediaStatus


def test_media_asset_defaults_and_database_constraints() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        owner = User(
            id=uuid4(),
            email="media-owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        owner_id = owner.id
        async with session_factory() as session:
            session.add(owner)
            await session.commit()

            asset = MediaAsset(
                owner_user_id=owner_id,
                cloudinary_public_id="ip-certificate/local/owner/avatar-1",
                resource_type="image",
                access_mode="authenticated",
                original_filename="avatar.png",
                mime_type="image/png",
                bytes=2_048,
            )
            session.add(asset)
            await session.commit()
            assert asset.status is MediaStatus.PENDING

            session.add(
                MediaAsset(
                    owner_user_id=owner_id,
                    cloudinary_public_id=asset.cloudinary_public_id,
                    resource_type="image",
                    access_mode="authenticated",
                    original_filename="duplicate.png",
                    mime_type="image/png",
                    bytes=1,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            session.add(
                MediaAsset(
                    owner_user_id=owner_id,
                    cloudinary_public_id="ip-certificate/local/owner/invalid-size",
                    resource_type="image",
                    access_mode="authenticated",
                    original_filename="invalid.png",
                    mime_type="image/png",
                    bytes=-1,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            session.add(
                MediaAsset(
                    owner_user_id=owner_id,
                    cloudinary_public_id="ip-certificate/local/owner/invalid-status",
                    resource_type="image",
                    access_mode="authenticated",
                    original_filename="invalid-status.png",
                    mime_type="image/png",
                    bytes=1,
                    status=cast(MediaStatus, "INVALID"),
                )
            )
            with pytest.raises(StatementError):
                await session.commit()
            await session.rollback()

        await engine.dispose()

    asyncio.run(exercise())
