import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.organizations.errors import (
    MembershipExistsError,
    OrganizationCodeExistsError,
    OrganizationForbiddenError,
    OrganizationOwnerOrphanError,
)
from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    Organization,
    OrganizationMember,
)
from app.modules.organizations.service import (
    CreateOrganization,
    OrganizationService,
    UpsertMember,
)
from app.modules.users.security import SensitiveFieldCipher


async def _build_service() -> tuple[
    OrganizationService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    dict[str, User],
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    users = {
        name: User(
            id=uuid4(),
            email=f"{name}@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        for name in ("owner", "manager", "member", "stranger")
    }
    async with session_factory() as session:
        session.add_all(users.values())
        await session.commit()

    service = OrganizationService(
        session=session_factory(),
        cipher=SensitiveFieldCipher(key=bytes(range(32))),
        clock=lambda: datetime(2026, 7, 30, 8, 0, tzinfo=UTC),
    )
    return service, session_factory, engine, users


def _principal(user: User) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=("APPLICANT",),
    )


def test_create_organization_adds_owner_and_encrypts_tax_code() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users = await _build_service()
        owner = _principal(users["owner"])

        created = await service.create_organization(
            owner,
            CreateOrganization(
                code="tmi-lab",
                legal_name="Công ty TMI Lab",
                display_name="TMI Lab",
                tax_code="0312345678",
            ),
        )

        assert created.code == "TMI-LAB"
        assert created.current_role is MembershipRole.OWNER
        assert created.can_manage_members is True
        async with session_factory() as session:
            organization = await session.get(Organization, created.id)
            membership = await session.get(
                OrganizationMember,
                (created.id, users["owner"].id),
            )
            assert organization is not None
            assert organization.tax_code_encrypted is not None
            assert b"0312345678" not in organization.tax_code_encrypted
            assert membership is not None
            assert membership.role_code is MembershipRole.OWNER
            assert membership.status is MembershipStatus.ACTIVE

        with pytest.raises(OrganizationCodeExistsError):
            await service.create_organization(
                owner,
                CreateOrganization(
                    code="TMI-LAB",
                    legal_name="Tên khác",
                    display_name="Tên khác",
                ),
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_membership_scope_unique_and_owner_protection() -> None:
    async def exercise() -> None:
        service, _, engine, users = await _build_service()
        owner = _principal(users["owner"])
        organization = await service.create_organization(
            owner,
            CreateOrganization(
                code="ORG-001",
                legal_name="Tổ chức số một",
                display_name="Tổ chức 1",
            ),
        )
        await service.add_member(
            owner,
            organization_id=organization.id,
            member=UpsertMember(
                email=users["manager"].email,
                role_code=MembershipRole.ORG_MANAGER,
                status=MembershipStatus.ACTIVE,
            ),
        )

        manager = _principal(users["manager"])
        added = await service.add_member(
            manager,
            organization_id=organization.id,
            member=UpsertMember(
                email=users["member"].email,
                role_code=MembershipRole.MEMBER,
                status=MembershipStatus.INVITED,
            ),
        )
        assert added.status is MembershipStatus.INVITED
        assert added.joined_at is None

        with pytest.raises(MembershipExistsError):
            await service.add_member(
                owner,
                organization_id=organization.id,
                member=UpsertMember(
                    email=users["member"].email,
                    role_code=MembershipRole.MEMBER,
                    status=MembershipStatus.ACTIVE,
                ),
            )
        with pytest.raises(OrganizationForbiddenError):
            await service.add_member(
                _principal(users["stranger"]),
                organization_id=organization.id,
                member=UpsertMember(
                    email=users["stranger"].email,
                    role_code=MembershipRole.MEMBER,
                    status=MembershipStatus.ACTIVE,
                ),
            )
        with pytest.raises(OrganizationOwnerOrphanError):
            await service.remove_member(
                owner,
                organization_id=organization.id,
                user_id=users["owner"].id,
            )

        await service.remove_member(
            manager,
            organization_id=organization.id,
            user_id=users["member"].id,
        )
        members = await service.list_members(owner, organization.id)
        assert {item.email for item in members.items} == {
            users["owner"].email,
            users["manager"].email,
        }

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
