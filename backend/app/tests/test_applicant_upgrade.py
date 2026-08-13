import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.errors import ApplicantUpgradeNotAllowedError
from app.modules.auth.models import AccountType, Role, User, UserRole, UserStatus
from app.modules.auth.onboarding import ApplicantUpgradeService
from app.modules.auth.session_service import AuthPrincipal


async def _build_session(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'upgrade.sqlite3').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return factory


def test_public_user_can_upgrade_once_without_privileged_role(tmp_path: Path) -> None:
    async def exercise() -> None:
        factory = await _build_session(tmp_path)
        user_id = uuid4()
        async with factory() as session:
            user = User(
                id=user_id,
                email="viewer@tmigroup.vn",
                status=UserStatus.ACTIVE,
                email_verified_at=datetime.now(UTC),
                account_type=AccountType.PUBLIC_USER,
            )
            role = Role(code="APPLICANT")
            session.add_all([user, role])
            await session.flush()
            await session.commit()
            principal = AuthPrincipal(
                user_id=user_id,
                session_id=uuid4(),
                email=user.email,
                roles=(),
                account_type=AccountType.PUBLIC_USER,
            )
            service = ApplicantUpgradeService(session=session)
            result = await service.upgrade(
                principal,
                account_type=AccountType.ORGANIZATION_APPLICANT,
            )
            result_again = await service.upgrade(
                AuthPrincipal(
                    user_id=principal.user_id,
                    session_id=principal.session_id,
                    email=principal.email,
                    roles=("APPLICANT",),
                    account_type=AccountType.ORGANIZATION_APPLICANT,
                ),
                account_type=AccountType.ORGANIZATION_APPLICANT,
            )
            assert result.account_type is AccountType.ORGANIZATION_APPLICANT
            assert result.roles == ("APPLICANT",)
            assert result_again == result

            stored_user = await session.get(User, user_id)
            stored_roles = tuple(
                (
                    await session.scalars(
                        select(Role.code)
                        .join(UserRole, UserRole.role_id == Role.id)
                        .where(UserRole.user_id == user_id)
                    )
                ).all()
            )
            assert stored_user is not None
            assert stored_user.account_type is AccountType.ORGANIZATION_APPLICANT
            assert stored_roles == ("APPLICANT",)
            audit_rows = (
                await session.scalars(
                    select(AuditLog).where(
                        AuditLog.action == "auth.account.applicant_upgraded"
                    )
                )
            ).all()
            assert len(audit_rows) == 1
            assert audit_rows[0].actor_user_id == user_id
            assert audit_rows[0].resource_id == str(user_id)
            assert audit_rows[0].after_json == {
                "account_type": "ORGANIZATION_APPLICANT"
            }
            assert "viewer@tmigroup.vn" not in str(audit_rows[0].after_json)

    asyncio.run(exercise())


def test_applicant_upgrade_rejects_non_public_account(tmp_path: Path) -> None:
    async def exercise() -> None:
        factory = await _build_session(tmp_path)
        async with factory() as session:
            user = User(
                email="applicant@tmigroup.vn",
                status=UserStatus.ACTIVE,
                email_verified_at=datetime.now(UTC),
                account_type=AccountType.INDIVIDUAL_APPLICANT,
            )
            session.add(user)
            await session.flush()
            await session.commit()
            principal = AuthPrincipal(
                user_id=user.id,
                session_id=uuid4(),
                email=user.email,
                roles=("APPLICANT",),
                account_type=AccountType.INDIVIDUAL_APPLICANT,
            )
            with pytest.raises(ApplicantUpgradeNotAllowedError):
                await ApplicantUpgradeService(session=session).upgrade(
                    principal,
                    account_type=AccountType.ORGANIZATION_APPLICANT,
                )

    asyncio.run(exercise())
