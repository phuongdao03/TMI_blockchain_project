import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.users.models import UserProfile
from app.modules.users.security import SensitiveFieldCipher
from app.modules.users.service import ProfileChanges, UserProfileService


async def _build_service() -> tuple[
    UserProfileService,
    async_sessionmaker[AsyncSession],
    User,
    AsyncEngine,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    user = User(
        id=uuid4(),
        email="owner@tmigroup.vn",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
    async with session_factory() as session:
        session.add(user)
        await session.commit()

    session = session_factory()
    service = UserProfileService(
        session=session,
        cipher=SensitiveFieldCipher(key=bytes(range(32))),
    )
    return service, session_factory, user, engine


def test_profile_defaults_then_persists_encrypted_phone() -> None:
    async def exercise() -> None:
        service, session_factory, user, engine = await _build_service()

        empty_profile = await service.get_profile(
            user_id=user.id,
            email=user.email,
        )
        assert empty_profile.full_name is None
        assert empty_profile.locale == "vi"
        assert empty_profile.timezone == "Asia/Ho_Chi_Minh"

        updated = await service.update_profile(
            user_id=user.id,
            email=user.email,
            changes=ProfileChanges(
                full_name="Nguyễn Minh Anh",
                phone="+84901234567",
                locale="vi",
                timezone="Asia/Ho_Chi_Minh",
                provided_fields=frozenset({"full_name", "phone", "locale", "timezone"}),
            ),
        )

        assert updated.full_name == "Nguyễn Minh Anh"
        assert updated.phone == "+84901234567"
        async with session_factory() as session:
            stored = await session.get(UserProfile, user.id)
            assert stored is not None
            assert stored.phone_encrypted is not None
            assert b"+84901234567" not in stored.phone_encrypted

        reread = await service.get_profile(user_id=user.id, email=user.email)
        assert reread.phone == "+84901234567"
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_profile_patch_only_changes_provided_fields() -> None:
    async def exercise() -> None:
        service, _, user, engine = await _build_service()
        await service.update_profile(
            user_id=user.id,
            email=user.email,
            changes=ProfileChanges(
                full_name="Tên ban đầu",
                phone="+84909999999",
                provided_fields=frozenset({"full_name", "phone"}),
            ),
        )

        updated = await service.update_profile(
            user_id=user.id,
            email=user.email,
            changes=ProfileChanges(
                full_name="Tên mới",
                provided_fields=frozenset({"full_name"}),
            ),
        )

        assert updated.full_name == "Tên mới"
        assert updated.phone == "+84909999999"
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
