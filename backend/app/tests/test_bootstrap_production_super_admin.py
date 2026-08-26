import asyncio
from typing import cast

import pytest
from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.scripts.bootstrap_production_super_admin import (
    ProductionFirebaseIdentity,
    provision_production_super_admin,
)


async def _factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = cast(
        list[Table],
        [User.__table__, Role.__table__, AuthIdentity.__table__, UserRole.__table__],
    )
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables))
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def test_production_bootstrap_links_firebase_uid_and_is_idempotent() -> None:
    async def scenario() -> None:
        engine, factory = await _factory()
        identity = ProductionFirebaseIdentity(
            email="operator@example.test",
            provider_subject="firebase-production-super-admin",
        )
        async with factory() as session:
            session.add_all([Role(code="SUPER_ADMIN"), Role(code="VIEWER")])
            await session.commit()

            first = await provision_production_super_admin(session, identity)
            second = await provision_production_super_admin(session, identity)

            assert first == second
            user = await session.get(User, first)
            assert user is not None
            assert user.status is UserStatus.ACTIVE
            assert user.email_verified_at is not None
            assert await session.scalar(select(func.count(User.id))) == 1
            linked_subject = await session.scalar(
                select(AuthIdentity.provider_subject).where(
                    AuthIdentity.user_id == first,
                    AuthIdentity.provider == AuthProvider.FIREBASE,
                )
            )
            assert linked_subject == identity.provider_subject
            roles = set(
                (
                    await session.scalars(
                        select(Role.code)
                        .join(UserRole, UserRole.role_id == Role.id)
                        .where(UserRole.user_id == first)
                    )
                ).all()
            )
            assert roles == {"SUPER_ADMIN"}
        await engine.dispose()

    asyncio.run(scenario())


def test_production_bootstrap_refuses_a_second_super_admin() -> None:
    async def scenario() -> None:
        engine, factory = await _factory()
        async with factory() as session:
            role = Role(code="SUPER_ADMIN")
            existing = User(email="existing@example.test", status=UserStatus.ACTIVE)
            session.add_all([role, existing])
            await session.flush()
            session.add(UserRole(user_id=existing.id, role_id=role.id))
            await session.commit()

            with pytest.raises(RuntimeError, match="already assigned"):
                await provision_production_super_admin(
                    session,
                    ProductionFirebaseIdentity(
                        email="other@example.test",
                        provider_subject="firebase-other",
                    ),
                )
        await engine.dispose()

    asyncio.run(scenario())


def test_production_bootstrap_refuses_firebase_uid_collision() -> None:
    async def scenario() -> None:
        engine, factory = await _factory()
        async with factory() as session:
            role = Role(code="SUPER_ADMIN")
            existing = User(email="existing@example.test", status=UserStatus.ACTIVE)
            session.add_all([role, existing])
            await session.flush()
            session.add(
                AuthIdentity(
                    user_id=existing.id,
                    provider=AuthProvider.FIREBASE,
                    provider_subject="firebase-collision",
                )
            )
            await session.commit()

            with pytest.raises(RuntimeError, match="already linked"):
                await provision_production_super_admin(
                    session,
                    ProductionFirebaseIdentity(
                        email="operator@example.test",
                        provider_subject="firebase-collision",
                    ),
                )
        await engine.dispose()

    asyncio.run(scenario())
