import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.work_allocations.models import (
    AllocationMember,
    WorkAllocation,
    WorkScope,
)
from app.modules.work_allocations.schemas import (
    ActivateWorkAllocationRequest,
    CreateWorkAllocationRequest,
)
from app.modules.work_allocations.service import WorkAllocationService


def _principal(
    *, user_id: UUID, role: str, permissions: tuple[str, ...] = ()
) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=uuid4(),
        email=f"{role.lower()}@example.com",
        roles=(role,),
        permissions=permissions,
    )


def test_work_allocation_roles_and_personal_list_enforce_boundaries() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(
                    sync_connection,
                    tables=[
                        User.__table__,
                        Role.__table__,
                        UserRole.__table__,
                        AuditLog.__table__,
                        WorkAllocation.__table__,
                        WorkScope.__table__,
                        AllocationMember.__table__,
                    ],
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin_id = uuid4()
        moderator_id = uuid4()
        moderator_role_id = uuid4()
        async with sessions.begin() as session:
            session.add_all(
                [
                    User(id=admin_id, email="admin@example.com", password_hash=None),
                    User(
                        id=moderator_id,
                        email="moderator@example.com",
                        password_hash=None,
                        status=UserStatus.ACTIVE,
                    ),
                    Role(id=moderator_role_id, code="MODERATOR"),
                    UserRole(user_id=moderator_id, role_id=moderator_role_id),
                ]
            )

        admin = _principal(user_id=admin_id, role="SUPER_ADMIN")
        moderator = _principal(user_id=moderator_id, role="MODERATOR")
        async with sessions() as session:
            service = WorkAllocationService(session)
            created = await service.create_allocation(
                admin,
                CreateWorkAllocationRequest.model_validate(
                    {
                        "kind": "GENERIC",
                        "objective": "Coordinate translation review",
                        "members": [
                            {
                                "userId": str(moderator_id),
                                "responsibility": "LEAD",
                            }
                        ],
                    }
                ),
                audit=AuditService(session),
                request_id="allocation-test",
                user_agent="pytest",
            )
            assert created.status.value == "DRAFT"

            mine, total = await service.list_my_allocations(
                moderator, page=1, page_size=20
            )
            assert total == 1
            assert mine[0].id == created.id

            audit = await session.scalar(
                select(AuditLog).where(AuditLog.action == "work.allocation.created")
            )
            assert audit is not None
            assert "description" not in audit.after_json
            assert "members" not in audit.after_json

            await session.execute(
                delete(UserRole).where(UserRole.user_id == moderator_id)
            )
            await session.commit()
            with pytest.raises(DomainError) as activation_error:
                await service.activate_allocation(
                    admin,
                    created.id,
                    ActivateWorkAllocationRequest(scope_coverage=[]),
                    audit=AuditService(session),
                    request_id="allocation-test",
                    user_agent="pytest",
                )
            assert activation_error.value.code == "WORK_ALLOCATION_MEMBER_INELIGIBLE"

            for role in ("VIEWER", "USER", "MODERATOR"):
                principal = (
                    moderator
                    if role == "MODERATOR"
                    else _principal(
                        user_id=uuid4(),
                        role=role,
                        permissions=("work.allocations.manage",),
                    )
                )
                with pytest.raises(DomainError) as creation_error:
                    await service.create_allocation(
                        principal,
                        CreateWorkAllocationRequest(
                            kind="GENERIC", objective="Unauthorized allocation"
                        ),
                        audit=AuditService(session),
                        request_id="allocation-test",
                        user_agent="pytest",
                    )
                assert creation_error.value.code == "WORK_ALLOCATION_FORBIDDEN"

            for role in ("VIEWER", "USER"):
                with pytest.raises(DomainError) as list_error:
                    await service.list_my_allocations(
                        _principal(user_id=uuid4(), role=role), page=1, page_size=20
                    )
                assert list_error.value.code == "WORK_ALLOCATION_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())


def test_work_allocation_requires_active_moderator_members() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(
                    sync_connection,
                    tables=[
                        User.__table__,
                        Role.__table__,
                        UserRole.__table__,
                        AuditLog.__table__,
                        WorkAllocation.__table__,
                        AllocationMember.__table__,
                    ],
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin_id = uuid4()
        ineligible_member_id = uuid4()
        user_role_id = uuid4()
        async with sessions.begin() as session:
            session.add_all(
                [
                    User(id=admin_id, email="admin@example.com", password_hash=None),
                    User(
                        id=ineligible_member_id,
                        email="employee@example.com",
                        password_hash=None,
                        status=UserStatus.ACTIVE,
                    ),
                    Role(id=user_role_id, code="USER"),
                    UserRole(user_id=ineligible_member_id, role_id=user_role_id),
                ]
            )

        async with sessions() as session:
            with pytest.raises(DomainError) as error:
                await WorkAllocationService(session).create_allocation(
                    _principal(user_id=admin_id, role="SUPER_ADMIN"),
                    CreateWorkAllocationRequest.model_validate(
                        {
                            "kind": "GENERIC",
                            "objective": "Invalid participant",
                            "members": [
                                {
                                    "userId": str(ineligible_member_id),
                                    "responsibility": "CONTRIBUTOR",
                                }
                            ],
                        }
                    ),
                    audit=AuditService(session),
                    request_id="allocation-test",
                    user_agent="pytest",
                )
            assert error.value.code == "WORK_ALLOCATION_MEMBER_INELIGIBLE"
            assert error.value.details == {"member_ids": [str(ineligible_member_id)]}
        await engine.dispose()

    asyncio.run(exercise())
