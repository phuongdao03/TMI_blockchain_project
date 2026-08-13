import asyncio
from typing import cast

from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import (
    AccountType,
    AuthIdentity,
    Role,
    User,
    UserRole,
)
from app.scripts.seed_local import LocalIdentity, seed_database


def test_local_database_seed_is_idempotent() -> None:
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
        identities = (
            LocalIdentity(
                email="applicant@example.com",
                provider_subject="firebase-local-1",
                role_code="APPLICANT",
                account_type=AccountType.INDIVIDUAL_APPLICANT,
            ),
            LocalIdentity(
                email="admin@example.com",
                provider_subject="firebase-local-2",
                role_code="SUPER_ADMIN",
                account_type=None,
            ),
        )
        async with factory() as session:
            await seed_database(session, identities)
            await seed_database(session, identities)
            assert await session.scalar(select(func.count(User.id))) == 2
            assert await session.scalar(select(func.count(Role.id))) == 2
            assert await session.scalar(select(func.count(AuthIdentity.id))) == 2
            assert await session.scalar(select(func.count()).select_from(UserRole)) == 2
        await engine.dispose()

    asyncio.run(scenario())
