import asyncio
from typing import cast

from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.audit.service import AuditService
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    AuthSession,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.scripts.bootstrap_production_super_admin import ProductionFirebaseIdentity
from app.scripts.recover_production_super_admin import (
    recover_production_super_admin,
)


async def _factory() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = cast(
        list[Table],
        [
            User.__table__,
            Role.__table__,
            AuthIdentity.__table__,
            AuthSession.__table__,
            UserRole.__table__,
        ],
    )
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables))
    return engine, async_sessionmaker(engine, expire_on_commit=False)


class _AuditRecorder:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def record(self, **kwargs: object) -> None:
        self.records.append(kwargs)


def test_recovery_replaces_existing_super_admin_and_preserves_old_account_audit() -> (
    None
):
    async def scenario() -> None:
        engine, factory = await _factory()
        async with factory() as session:
            audit = _AuditRecorder()
            super_admin = Role(code="SUPER_ADMIN")
            old_admin = User(email="old-admin@example.test", status=UserStatus.ACTIVE)
            session.add_all([super_admin, old_admin])
            await session.flush()
            session.add_all(
                [
                    UserRole(user_id=old_admin.id, role_id=super_admin.id),
                    AuthIdentity(
                        user_id=old_admin.id,
                        provider=AuthProvider.FIREBASE,
                        provider_subject="firebase-old-admin",
                    ),
                    AuthSession(
                        user_id=old_admin.id,
                        refresh_token_hash="r" * 64,
                        expires_at=old_admin.created_at,
                    ),
                ]
            )
            await session.commit()

            result = await recover_production_super_admin(
                session,
                ProductionFirebaseIdentity(
                    email="blockchainadmin@gmail.com",
                    provider_subject="kRDCuJDD73dni8w7tgN4SLXwy3O2",
                ),
                audit=cast(AuditService, audit),
            )

            assert result.decommissioned_user_ids == (old_admin.id,)
            old = await session.get(User, old_admin.id)
            assert old is not None
            await session.refresh(old)
            assert old.status is UserStatus.DELETED
            assert old.disabled_at is not None
            assert old.deleted_at is not None
            assert (
                await session.scalar(
                    select(func.count(UserRole.user_id)).where(
                        UserRole.user_id == old_admin.id,
                        UserRole.role_id == super_admin.id,
                    )
                )
                == 0
            )
            assert (
                await session.scalar(
                    select(AuthSession.revoked_at).where(
                        AuthSession.user_id == old_admin.id
                    )
                )
                is not None
            )

            new_admin = await session.get(User, result.user_id)
            assert new_admin is not None
            assert new_admin.email == "blockchainadmin@gmail.com"
            assert new_admin.status is UserStatus.ACTIVE
            assert (
                await session.scalar(
                    select(func.count(UserRole.user_id)).where(
                        UserRole.user_id == new_admin.id,
                        UserRole.role_id == super_admin.id,
                    )
                )
                == 1
            )
            assert [record["action"] for record in audit.records] == [
                "production.super_admin.decommissioned",
                "production.super_admin.recovered",
            ]
        await engine.dispose()

    asyncio.run(scenario())
