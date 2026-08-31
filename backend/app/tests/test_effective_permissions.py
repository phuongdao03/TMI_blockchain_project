import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserPermission,
    UserRole,
)
from app.modules.auth.repositories import AuthRepository


def test_effective_permissions_union_role_and_active_user_grants(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        database_path = tmp_path / "effective-permissions.sqlite3"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(UTC)
        user = User(id=uuid4(), email="operator@example.test", password_hash=None)
        grantor = User(id=uuid4(), email="grantor@example.test", password_hash=None)
        role = Role(id=uuid4(), code="USER")
        role_permission = Permission(id=uuid4(), code="submissions.read")
        direct_permission = Permission(id=uuid4(), code="payments.read")
        expired_permission = Permission(id=uuid4(), code="users.suspend")

        async with factory() as session:
            session.add_all(
                [
                    user,
                    grantor,
                    role,
                    role_permission,
                    direct_permission,
                    expired_permission,
                    UserRole(user_id=user.id, role_id=role.id),
                    RolePermission(
                        role_id=role.id,
                        permission_id=role_permission.id,
                    ),
                    UserPermission(
                        user_id=user.id,
                        permission_id=direct_permission.id,
                        granted_by_user_id=grantor.id,
                        reason="Finance operations assignment",
                        expires_at=now + timedelta(hours=1),
                    ),
                    UserPermission(
                        user_id=user.id,
                        permission_id=expired_permission.id,
                        granted_by_user_id=grantor.id,
                        reason="Expired temporary assignment",
                        expires_at=now - timedelta(seconds=1),
                    ),
                ]
            )
            await session.commit()

            assert await AuthRepository(session).get_permission_codes(user.id) == (
                "payments.read",
                "submissions.read",
            )
        await engine.dispose()

    asyncio.run(exercise())
