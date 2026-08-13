import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import AccountType, User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.errors import (
    ApplicantProfileIncompleteError,
    DossierForbiddenError,
    DossierInvalidStateError,
    DossierNotFoundError,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierStatus,
    DossierVisibility,
)
from app.modules.dossiers.service import DossierService
from app.modules.dossiers.types import CreateDossier, DossierChanges
from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    Organization,
    OrganizationMember,
)
from app.modules.users.models import UserProfile

CATEGORY_ID = UUID("4d28db19-1507-5a45-a50d-cd0aa83029ec")
NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


async def _build_service() -> tuple[
    DossierService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    dict[str, User],
    Organization,
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
    organization = Organization(
        id=uuid4(),
        code="TMI-LAB",
        legal_name="TMI Lab",
        display_name="TMI Lab",
        owner_user_id=users["manager"].id,
    )
    async with session_factory() as session:
        session.add_all(
            [
                *users.values(),
                Category(
                    id=CATEGORY_ID,
                    code="DIGITAL_INTELLECTUAL_ASSET",
                    name="Tài sản trí tuệ số",
                ),
                organization,
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=users["manager"].id,
                    role_code=MembershipRole.OWNER,
                    status=MembershipStatus.ACTIVE,
                    joined_at=NOW,
                ),
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=users["member"].id,
                    role_code=MembershipRole.MEMBER,
                    status=MembershipStatus.ACTIVE,
                    joined_at=NOW,
                ),
            ]
        )
        await session.commit()

    service = DossierService(
        session=session_factory(),
        clock=lambda: NOW,
        uuid_factory=lambda: UUID("17c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
    )
    return service, session_factory, engine, users, organization


def _principal(user: User, *roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=roles or ("APPLICANT",),
    )


def test_owner_can_create_list_update_and_soft_delete_draft() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, _ = await _build_service()
        principal = _principal(users["owner"])

        created = await service.create_dossier(
            principal,
            CreateDossier(
                category_id=CATEGORY_ID,
                title="  Bộ nhận diện TMI  ",
                summary="Bản mô tả quyền sở hữu.",
                visibility=DossierVisibility.PRIVATE,
            ),
        )
        assert created.code == "TMI-2026-17C53B2935EA"
        assert created.title == "Bộ nhận diện TMI"
        assert created.status is DossierStatus.DRAFT

        listed = await service.list_dossiers(
            principal,
            status=DossierStatus.DRAFT,
            category_id=CATEGORY_ID,
        )
        assert listed.total == 1
        assert listed.items[0].id == created.id

        updated = await service.update_dossier(
            principal,
            created.id,
            DossierChanges(
                title="Bộ nhận diện TMI Group",
                summary=None,
                provided_fields=frozenset({"title", "summary"}),
            ),
        )
        assert updated.title == "Bộ nhận diện TMI Group"
        assert updated.summary is None

        await service.delete_dossier(principal, created.id)
        with pytest.raises(DossierNotFoundError):
            await service.get_dossier(principal, created.id)
        async with session_factory() as session:
            dossier = await session.get(Dossier, created.id)
            assert dossier is not None
            assert dossier.deleted_at is not None
            assert dossier.deleted_at.replace(tzinfo=UTC) == NOW
            audit_rows = tuple(
                (
                    await session.scalars(
                        select(AuditLog)
                        .where(AuditLog.resource_id == str(created.id))
                        .order_by(AuditLog.created_at, AuditLog.action)
                    )
                ).all()
            )
            assert {row.action for row in audit_rows} == {
                "dossier.created",
                "dossier.deleted",
                "dossier.updated",
            }
            assert all(row.actor_user_id == principal.user_id for row in audit_rows)
            assert all(row.resource_type == "dossier" for row in audit_rows)

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_dossier_and_audit_record_roll_back_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, _ = await _build_service()
        principal = _principal(users["owner"])

        def fail_audit(**_: object) -> None:
            raise RuntimeError("audit storage unavailable")

        monkeypatch.setattr(service._audit_service, "record", fail_audit)
        with pytest.raises(RuntimeError, match="audit storage unavailable"):
            await service.create_dossier(
                principal,
                CreateDossier(
                    category_id=CATEGORY_ID,
                    title="Hồ sơ phải rollback",
                    visibility=DossierVisibility.PRIVATE,
                ),
            )

        async with session_factory() as session:
            assert (await session.scalar(select(Dossier))) is None
            assert (await session.scalar(select(AuditLog))) is None

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_applicant_must_complete_profile_before_creating_dossier() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, _ = await _build_service()
        principal = AuthPrincipal(
            user_id=users["owner"].id,
            session_id=uuid4(),
            email=users["owner"].email,
            roles=("APPLICANT",),
            account_type=AccountType.INDIVIDUAL_APPLICANT,
        )

        with pytest.raises(ApplicantProfileIncompleteError):
            await service.create_dossier(
                principal,
                CreateDossier(
                    category_id=CATEGORY_ID,
                    title="Profile incomplete",
                ),
            )

        async with session_factory() as session:
            session.add(
                UserProfile(
                    user_id=users["owner"].id,
                    full_name="Applicant owner",
                )
            )
            await session.commit()

        created = await service.create_dossier(
            principal,
            CreateDossier(category_id=CATEGORY_ID, title="Profile complete"),
        )
        assert created.title == "Profile complete"

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_organization_scope_allows_read_but_only_manager_mutation() -> None:
    async def exercise() -> None:
        service, _, engine, users, organization = await _build_service()
        manager = _principal(users["manager"], "ORG_MANAGER")
        created = await service.create_dossier(
            manager,
            CreateDossier(
                category_id=CATEGORY_ID,
                organization_id=organization.id,
                title="Hồ sơ tổ chức",
            ),
        )

        member_view = await service.get_dossier(
            _principal(users["member"]),
            created.id,
        )
        assert member_view.id == created.id
        with pytest.raises(DossierForbiddenError):
            await service.update_dossier(
                _principal(users["member"]),
                created.id,
                DossierChanges(
                    title="Không được phép",
                    provided_fields=frozenset({"title"}),
                ),
            )
        with pytest.raises(DossierForbiddenError):
            await service.get_dossier(
                _principal(users["stranger"]),
                created.id,
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_invalid_category_role_and_non_editable_state_are_rejected() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, _ = await _build_service()
        owner = _principal(users["owner"])

        with pytest.raises(DossierNotFoundError):
            await service.create_dossier(
                owner,
                CreateDossier(category_id=uuid4(), title="Sai danh mục"),
            )
        with pytest.raises(DossierForbiddenError):
            await service.create_dossier(
                _principal(users["owner"], "REVIEWER"),
                CreateDossier(category_id=CATEGORY_ID, title="Sai vai trò"),
            )

        created = await service.create_dossier(
            owner,
            CreateDossier(category_id=CATEGORY_ID, title="Đã nộp"),
        )
        async with session_factory() as session:
            async with session.begin():
                dossier = await session.get(Dossier, created.id)
                assert dossier is not None
                dossier._set_status_from_workflow(DossierStatus.SUBMITTED)

        with pytest.raises(DossierInvalidStateError):
            await service.update_dossier(
                owner,
                created.id,
                DossierChanges(
                    title="Không thể sửa",
                    provided_fields=frozenset({"title"}),
                ),
            )
        with pytest.raises(DossierInvalidStateError):
            await service.delete_dossier(owner, created.id)

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
