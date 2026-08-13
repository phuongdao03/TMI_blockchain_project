from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.service import AuditService
from app.modules.auth.models import AuthSession, Role, User, UserRole, UserStatus
from app.modules.auth.schemas import StaffAccountUpdateRequest
from app.modules.auth.session_service import AuthPrincipal
from app.modules.auth.staff_account_service import StaffAccountService


def principal(*roles: str, permissions: tuple[str, ...] = ()) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="admin@tmigroup.vn",
        roles=roles,
        permissions=permissions,
    )


def test_staff_management_requires_super_admin() -> None:
    with pytest.raises(DomainError) as captured:
        StaffAccountService.require_super_admin(principal("CONTENT_ADMIN"))

    assert captured.value.code == "STAFF_ACCOUNT_FORBIDDEN"
    assert captured.value.status_code == 403


def test_staff_management_accepts_normalized_permission() -> None:
    StaffAccountService.require_super_admin(
        principal("AUDITOR", permissions=("admin.staff.manage",))
    )


def test_staff_update_rejects_self_suspend_before_database_work() -> None:
    service = StaffAccountService(cast(AsyncSession, None))
    admin = principal("SUPER_ADMIN")

    async def scenario() -> None:
        with pytest.raises(DomainError) as captured:
            await service.update(
                user_id=admin.user_id,
                payload=StaffAccountUpdateRequest(status="SUSPENDED"),
                principal=admin,
                audit=cast(AuditService, None),
                request_id=None,
                user_agent=None,
            )
        assert captured.value.code == "STAFF_ACCOUNT_SELF_SUSPEND"

    import asyncio

    asyncio.run(scenario())


def test_staff_data_mapping_never_contains_password_fields() -> None:
    user = User(
        id=uuid4(),
        email="reviewer@tmigroup.vn",
        password_hash="hashed-secret",
        status=UserStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )

    data = StaffAccountService._to_data(user, "REVIEWER")

    assert data.email == "reviewer@tmigroup.vn"
    assert "password" not in data.model_dump()


def test_disable_is_non_destructive_revokes_sessions_and_cannot_be_bypassed(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'disable-staff.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        admin = principal("SUPER_ADMIN")
        async with factory.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, status="ACTIVE"))
            target = User(email="reviewer@example.com", status=UserStatus.ACTIVE)
            role = Role(code="REVIEWER")
            session.add_all((target, role))
            await session.flush()
            session.add_all(
                (
                    UserRole(user_id=target.id, role_id=role.id),
                    AuthSession(
                        user_id=target.id,
                        refresh_token_hash="b" * 64,
                        expires_at=datetime.now(UTC) + timedelta(days=1),
                    ),
                )
            )
            target_id = target.id

        async with factory() as session:
            disabled = await StaffAccountService(session).update(
                user_id=target_id,
                payload=StaffAccountUpdateRequest(status="DISABLED"),
                principal=admin,
                audit=AuditService(session),
                request_id="disable-1",
                user_agent="test",
            )
            assert disabled.status == "DISABLED"

        async with factory() as session:
            stored = await session.get(User, target_id)
            auth_session = (
                await session.scalars(
                    select(AuthSession).where(AuthSession.user_id == target_id)
                )
            ).one()
            assert stored is not None and stored.disabled_at is not None
            assert stored.deleted_at is None
            assert auth_session.revoked_at is not None
            await session.rollback()
            with pytest.raises(DomainError) as reactivation:
                await StaffAccountService(session).update(
                    user_id=target_id,
                    payload=StaffAccountUpdateRequest(status="ACTIVE"),
                    principal=admin,
                    audit=AuditService(session),
                    request_id="reactivate-1",
                    user_agent="test",
                )
            assert reactivation.value.code == "STAFF_ACCOUNT_DISABLED"
        await engine.dispose()

    import asyncio

    asyncio.run(scenario())
