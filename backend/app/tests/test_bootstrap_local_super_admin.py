import asyncio
from typing import cast

import pytest
from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import (
    AuthIdentity,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.scripts.bootstrap_local_super_admin import (
    LocalFirebaseIdentity,
    provision_super_admin,
)


def test_local_super_admin_bootstrap_is_idempotent() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        tables = cast(
            list[Table],
            [
                User.__table__,
                Role.__table__,
                AuthIdentity.__table__,
                UserRole.__table__,
            ],
        )
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: Base.metadata.create_all(sync, tables)
            )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        identity = LocalFirebaseIdentity(
            email="operator@example.test",
            provider_subject="firebase-local-super-admin",
        )
        async with factory() as session:
            session.add(Role(code="SUPER_ADMIN"))
            await session.commit()

            await provision_super_admin(session, identity)
            await provision_super_admin(session, identity)

            user = await session.scalar(
                select(User).where(User.email == identity.email)
            )
            assert user is not None
            assert user.status is UserStatus.ACTIVE
            assert user.email_verified_at is not None
            assert await session.scalar(select(func.count(User.id))) == 1
            assert await session.scalar(select(func.count(AuthIdentity.id))) == 1
            assert await session.scalar(select(func.count()).select_from(UserRole)) == 1
            assigned_role = await session.scalar(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user.id)
            )
            assert assigned_role == "SUPER_ADMIN"
        await engine.dispose()

    asyncio.run(scenario())


def test_local_super_admin_bootstrap_refuses_to_promote_existing_account() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        tables = cast(
            list[Table],
            [
                User.__table__,
                Role.__table__,
                AuthIdentity.__table__,
                UserRole.__table__,
            ],
        )
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: Base.metadata.create_all(sync, tables)
            )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        identity = LocalFirebaseIdentity(
            email="existing@example.test",
            provider_subject="firebase-local-existing",
        )
        async with factory() as session:
            viewer_role = Role(code="VIEWER")
            session.add_all(
                [
                    Role(code="SUPER_ADMIN"),
                    viewer_role,
                    User(email=identity.email, status=UserStatus.ACTIVE),
                ]
            )
            await session.flush()
            existing_user = await session.scalar(
                select(User).where(User.email == identity.email)
            )
            assert existing_user is not None
            existing_user_id = existing_user.id
            session.add(UserRole(user_id=existing_user_id, role_id=viewer_role.id))
            await session.commit()

            with pytest.raises(
                RuntimeError, match="existing account is not a super admin"
            ):
                await provision_super_admin(session, identity)

            assigned_role = await session.scalar(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == existing_user_id)
            )
            assert assigned_role == "VIEWER"
        await engine.dispose()

    asyncio.run(scenario())
