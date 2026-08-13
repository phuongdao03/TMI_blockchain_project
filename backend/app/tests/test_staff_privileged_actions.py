from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import (
    AuthSession,
    PrivilegedAction,
    PrivilegedActionStatus,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.modules.auth.schemas import PrivilegedActionRequest
from app.modules.auth.session_service import AuthPrincipal
from app.modules.auth.staff_privileged_action_service import (
    StaffPrivilegedActionService,
)

NOW = datetime(2026, 8, 10, 9, tzinfo=UTC)


def _principal(user_id: UUID, email: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=user_id,
        email=email,
        roles=("SUPER_ADMIN",),
        permissions=("admin.staff.manage", "admin.staff.approve"),
    )


def test_role_elevation_requires_distinct_approver_and_revokes_sessions(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'dual-control.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory.begin() as session:
            initiator = User(email="admin-1@example.com", status=UserStatus.ACTIVE)
            approver = User(email="admin-2@example.com", status=UserStatus.ACTIVE)
            target = User(email="reviewer@example.com", status=UserStatus.ACTIVE)
            super_role = Role(code="SUPER_ADMIN")
            reviewer_role = Role(code="REVIEWER")
            session.add_all((initiator, approver, target, super_role, reviewer_role))
            await session.flush()
            session.add_all(
                (
                    UserRole(user_id=initiator.id, role_id=super_role.id),
                    UserRole(user_id=approver.id, role_id=super_role.id),
                    UserRole(user_id=target.id, role_id=reviewer_role.id),
                    AuthSession(
                        user_id=target.id,
                        refresh_token_hash="a" * 64,
                        expires_at=NOW + timedelta(days=1),
                    ),
                )
            )
            initiator_id = initiator.id
            approver_id = approver.id
            target_id = target.id

        async with factory() as session:
            service = StaffPrivilegedActionService(session=session, clock=lambda: NOW)
            action = await service.request(
                target_user_id=target_id,
                payload=PrivilegedActionRequest(
                    action="ROLE_CHANGE",
                    requestedRole="SUPER_ADMIN",
                    reason="Appointment approved by executive management",
                ),
                principal=_principal(initiator_id, "admin-1@example.com"),
                audit=AuditService(session),
                request_id="request-1",
                user_agent="test",
            )
            assert action.status == "PENDING"
            with pytest.raises(DomainError) as self_approval:
                await service.approve(
                    action_id=action.id,
                    principal=_principal(initiator_id, "admin-1@example.com"),
                    audit=AuditService(session),
                    request_id="request-2",
                    user_agent="test",
                )
            assert self_approval.value.code == "PRIVILEGED_ACTION_SELF_APPROVAL"
            await session.rollback()

            approved = await service.approve(
                action_id=action.id,
                principal=_principal(approver_id, "admin-2@example.com"),
                audit=AuditService(session),
                request_id="request-3",
                user_agent="test",
            )
            assert approved.status == "APPROVED"

        async with factory() as session:
            roles = {
                role.code
                for role in (
                    await session.scalars(
                        select(Role)
                        .join(UserRole, UserRole.role_id == Role.id)
                        .where(UserRole.user_id == target_id)
                    )
                ).all()
            }
            auth_session = (
                await session.scalars(
                    select(AuthSession).where(AuthSession.user_id == target_id)
                )
            ).one()
            action_row = await session.get(PrivilegedAction, action.id)
            assert roles == {"SUPER_ADMIN"}
            assert auth_session.revoked_at is not None
            assert auth_session.revoked_at.replace(tzinfo=UTC) == NOW
            assert action_row is not None
            assert action_row.status is PrivilegedActionStatus.APPROVED
            assert action_row.approved_by_user_id == approver_id
            assert set((await session.scalars(select(AuditLog.action))).all()) == {
                "admin.privileged_action.requested",
                "admin.privileged_action.approved",
            }
        await engine.dispose()

    import asyncio

    asyncio.run(scenario())


def test_mfa_recovery_changes_state_only_after_second_approval(tmp_path: Path) -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'recovery-control.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory.begin() as session:
            first = User(email="admin-1@example.com", status=UserStatus.ACTIVE)
            second = User(email="admin-2@example.com", status=UserStatus.ACTIVE)
            staff = User(email="staff@example.com", status=UserStatus.ACTIVE)
            super_role = Role(code="SUPER_ADMIN")
            reviewer_role = Role(code="REVIEWER")
            session.add_all((first, second, staff, super_role, reviewer_role))
            await session.flush()
            session.add_all(
                (
                    UserRole(user_id=first.id, role_id=super_role.id),
                    UserRole(user_id=second.id, role_id=super_role.id),
                    UserRole(user_id=staff.id, role_id=reviewer_role.id),
                )
            )
            first_id, second_id, staff_id = first.id, second.id, staff.id

        async with factory() as session:
            service = StaffPrivilegedActionService(session=session, clock=lambda: NOW)
            action = await service.request(
                target_user_id=staff_id,
                payload=PrivilegedActionRequest(
                    action="MFA_RECOVERY",
                    reason="Employee replaced a lost managed device",
                ),
                principal=_principal(first_id, "admin-1@example.com"),
                audit=AuditService(session),
                request_id=None,
                user_agent=None,
            )
            unchanged = await session.get(User, staff_id)
            assert unchanged is not None
            assert unchanged.status is UserStatus.ACTIVE
            await session.commit()
            await service.approve(
                action_id=action.id,
                principal=_principal(second_id, "admin-2@example.com"),
                audit=AuditService(session),
                request_id=None,
                user_agent=None,
            )

        async with factory() as session:
            recovered = await session.get(User, staff_id)
            assert recovered is not None
            assert recovered.status is UserStatus.SUSPENDED
            assert recovered.mfa_recovery_authorized_at is not None
            assert recovered.mfa_recovery_authorized_at.replace(tzinfo=UTC) == NOW
        await engine.dispose()

    import asyncio

    asyncio.run(scenario())
