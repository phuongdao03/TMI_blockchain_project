import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.admin_users import router
from app.core.config import Settings
from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
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
from app.modules.auth.session_service import AuthPrincipal
from app.modules.users.admin_service import (
    AdminUserQuery,
    AdminUserService,
    AdminUserStatusRequest,
    SortField,
)
from app.modules.users.models import UserProfile


def _principal(*permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="operator@example.com",
        roles=("USER",),
        permissions=permissions,
    )


def test_admin_user_list_is_filtered_stable_and_permission_protected(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        database_path = tmp_path / "admin-users.sqlite3"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        role = Role(code="USER")
        minh = User(
            email="minh@example.com",
            password_hash=None,
            status=UserStatus.ACTIVE,
        )
        an = User(
            email="an@example.com",
            password_hash=None,
            status=UserStatus.SUSPENDED,
        )
        async with factory.begin() as session:
            session.add_all([role, minh, an])
            await session.flush()
            session.add_all(
                [
                    UserRole(user_id=minh.id, role_id=role.id),
                    UserRole(user_id=an.id, role_id=role.id),
                    UserProfile(user_id=minh.id, full_name="Nguyen Minh"),
                    UserProfile(user_id=an.id, full_name="Tran An"),
                    AuthIdentity(
                        user_id=minh.id,
                        provider=AuthProvider.GOOGLE,
                        provider_subject="google-minh",
                    ),
                ]
            )

        service_principal = _principal("users.read")
        async with factory() as session:
            rows, total = await AdminUserService(session).list(
                service_principal,
                AdminUserQuery(
                    page=1,
                    page_size=20,
                    search="minh",
                    status=UserStatus.ACTIVE,
                    provider=AuthProvider.GOOGLE,
                    verified=None,
                    sort_by="email",
                    sort_order="asc",
                ),
            )
            assert total == 1
            assert len(rows) == 1
            assert rows[0].email == "minh@example.com"
            assert rows[0].full_name == "Nguyen Minh"
            assert rows[0].providers == ("GOOGLE",)
            assert rows[0].roles == ("USER",)
            assert "password" not in rows[0].model_dump()

            detail = await AdminUserService(session).detail(service_principal, minh.id)
            assert detail.id == minh.id

        async with factory() as session:
            with pytest.raises(DomainError) as denied:
                await AdminUserService(session).list(
                    _principal(),
                    AdminUserQuery(page=1, page_size=20),
                )
            assert denied.value.status_code == 403
        await engine.dispose()

    asyncio.run(exercise())


def test_admin_user_query_rejects_unknown_sort_field() -> None:
    with pytest.raises(ValueError):
        AdminUserQuery(
            page=1,
            page_size=20,
            sort_by=cast(SortField, "passwordHash"),
        )


def test_admin_user_routes_are_plural_resource_contracts() -> None:
    contracts = {
        (route.path, frozenset(route.methods or set()))
        for route in router.routes
        if isinstance(route, APIRoute)
    }

    assert ("/api/v1/admin/users", frozenset({"GET"})) in contracts
    assert ("/api/v1/admin/users/{user_id}", frozenset({"GET"})) in contracts
    assert (
        "/api/v1/admin/users/{user_id}/status",
        frozenset({"PATCH"}),
    ) in contracts


def test_admin_user_suspension_revokes_sessions_and_writes_audit(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        class FakeFirebaseAdmin:
            def __init__(self) -> None:
                self.changes: list[tuple[str, bool]] = []

            async def set_disabled(self, uid: str, *, disabled: bool) -> None:
                self.changes.append((uid, disabled))

        database_path = tmp_path / "admin-user-suspend.sqlite3"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        target = User(
            email="target@example.com",
            password_hash=None,
            status=UserStatus.ACTIVE,
        )
        async with factory.begin() as session:
            session.add(target)
            await session.flush()
            session.add_all(
                [
                    AuthSession(
                        user_id=target.id,
                        refresh_token_hash="r" * 64,
                        expires_at=datetime.now(UTC) + timedelta(days=1),
                    ),
                    AuthIdentity(
                        user_id=target.id,
                        provider=AuthProvider.FIREBASE,
                        provider_subject="firebase-target",
                    ),
                ]
            )
        actor = _principal("users.suspend")
        firebase_admin = FakeFirebaseAdmin()
        async with factory() as session:
            result = await AdminUserService(
                session, firebase_admin=firebase_admin
            ).change_status(
                actor,
                target.id,
                AdminUserStatusRequest(
                    status=UserStatus.SUSPENDED,
                    expectedStatus=UserStatus.ACTIVE,
                    reason="Account activity requires investigation",
                ),
                audit=AuditService(session, settings=Settings.model_validate({})),
                request_id="suspend-1",
                user_agent="test-agent",
            )
            assert result.status is UserStatus.SUSPENDED
            assert firebase_admin.changes == [("firebase-target", True)]

        async with factory() as session:
            stored = await session.get(User, target.id)
            auth_session = (
                await session.scalars(
                    select(AuthSession).where(AuthSession.user_id == target.id)
                )
            ).one()
            audit = (await session.scalars(select(AuditLog))).one()
            assert stored is not None and stored.status is UserStatus.SUSPENDED
            assert auth_session.revoked_at is not None
            assert audit.before_json == {"status": "ACTIVE"}
            assert audit.after_json == {
                "reason": "Account activity requires investigation",
                "status": "SUSPENDED",
            }
        await engine.dispose()

    asyncio.run(exercise())
