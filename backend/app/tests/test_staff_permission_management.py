import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.staff_accounts import router
from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import Permission, User, UserPermission, UserStatus
from app.modules.auth.schemas import StaffPermissionReplaceRequest
from app.modules.auth.session_service import AuthPrincipal
from app.modules.auth.staff_account_service import StaffAccountService


def _principal(user_id: UUID | None = None, *permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id or uuid4(),
        session_id=uuid4(),
        email="admin@example.test",
        roles=("USER",),
        permissions=permissions,
    )


def test_permission_replacement_is_versioned_audited_and_default_deny(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        database_path = tmp_path / "staff-permissions.sqlite3"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        actor = _principal(None, "staff.permissions.assign", "payments.read")
        target = User(
            id=uuid4(),
            email="finance@example.test",
            password_hash=None,
            status=UserStatus.ACTIVE,
        )
        permission = Permission(id=uuid4(), code="payments.read")
        async with factory.begin() as session:
            session.add_all(
                [
                    User(
                        id=actor.user_id,
                        email=actor.email,
                        password_hash=None,
                        status=UserStatus.ACTIVE,
                    ),
                    target,
                    permission,
                ]
            )

        payload = StaffPermissionReplaceRequest(
            permissions=["payments.read"],
            expected_version=0,
            reason="Assign finance read operations",
        )
        async with factory() as session:
            result = await StaffAccountService(session).replace_permissions(
                user_id=target.id,
                payload=payload,
                principal=actor,
                audit=AuditService(session),
                request_id="permission-1",
                user_agent="test-agent",
            )
            assert result.version == 1
            assert result.permissions == ("payments.read",)

        async with factory() as session:
            grants = tuple((await session.scalars(select(UserPermission))).all())
            audit = tuple((await session.scalars(select(AuditLog))).all())
            assert len(grants) == 1
            assert audit[0].action == "admin.staff_permissions.replaced"
            assert audit[0].before_json == {"permissions": [], "version": 0}
            assert audit[0].after_json == {
                "permissions": ["payments.read"],
                "reason": "Assign finance read operations",
                "version": 1,
            }
            await session.rollback()

            with pytest.raises(DomainError) as stale:
                await StaffAccountService(session).replace_permissions(
                    user_id=target.id,
                    payload=payload,
                    principal=actor,
                    audit=AuditService(session),
                    request_id="permission-2",
                    user_agent="test-agent",
                )
            assert stale.value.code == "STAFF_PERMISSION_VERSION_CONFLICT"

        denied = _principal()
        async with factory() as session:
            with pytest.raises(DomainError) as forbidden:
                await StaffAccountService(session).get_permissions(target.id, denied)
            assert forbidden.value.status_code == 403

        await engine.dispose()

    asyncio.run(exercise())


def test_permission_replacement_rejects_self_escalation_before_database() -> None:
    actor = _principal(None, "staff.permissions.assign")
    service = StaffAccountService(None)  # type: ignore[arg-type]

    async def exercise() -> None:
        with pytest.raises(DomainError) as captured:
            await service.replace_permissions(
                user_id=actor.user_id,
                payload=StaffPermissionReplaceRequest(
                    permissions=["users.suspend"],
                    expected_version=0,
                    reason="Attempt to elevate own permissions",
                ),
                principal=actor,
                audit=None,  # type: ignore[arg-type]
                request_id=None,
                user_agent=None,
            )
        assert captured.value.code == "STAFF_PERMISSION_SELF_ASSIGNMENT"

    asyncio.run(exercise())


def test_staff_permission_routes_expose_read_and_csrf_protected_replace() -> None:
    methods_by_path = {
        route.path: route.methods
        for route in router.routes
        if isinstance(route, APIRoute)
    }

    assert methods_by_path["/api/v1/admin/staff-accounts/{user_id}/permissions"] == {
        "PUT"
    }
    assert any(
        route.path == "/api/v1/admin/staff-accounts/{user_id}/permissions"
        and route.methods == {"GET"}
        for route in router.routes
        if isinstance(route, APIRoute)
    )
