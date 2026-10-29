from app.modules.auth.models import Permission, UserPermission, RolePermission
import asyncio
import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI, Request
from pydantic import SecretStr
from sqlalchemy import MetaData, Table, create_engine, func, inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.vouchers import router
from app.core.config import Settings, get_settings
from app.core.errors import DomainError, install_exception_handlers
from app.db.base import Base
from app.db.session import get_session
from app.modules.auth.dependencies import (
    get_current_principal,
    get_employee_profile_link_status,
)
from app.modules.auth.errors import UnauthenticatedError
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.auth.tokens import CsrfTokenManager
from app.modules.hr.models import Department, Employee
from app.modules.notifications.models import Notification
from app.modules.promotions.models import (
    VoucherCampaign,
    VoucherClaim,
    VoucherPresentationState,
)
from app.modules.promotions.service import VoucherService


async def _seed_recipients(session):
    await session.flush()
    role = await session.scalar(select(Role).where(Role.code == "USER"))
    if role is None:
        role = Role(code="USER")
        session.add(role)
        await session.flush()
    for user_id in await session.scalars(select(User.id)):
        if await session.get(UserRole, (user_id, role.id)) is None:
            session.add(UserRole(user_id=user_id, role_id=role.id))
    await session.flush()


def test_claim_is_persistent_idempotent_and_account_scoped():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: Base.metadata.create_all(
                    c,
                    tables=[
                        User.__table__,
                        Role.__table__, Permission.__table__, UserPermission.__table__, RolePermission.__table__,
                        UserRole.__table__,
                        Department.__table__,
                        Employee.__table__,
                        Notification.__table__,
                        VoucherPresentationState.__table__,
                        VoucherCampaign.__table__,
                        VoucherClaim.__table__,
                    ],
                )
            )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime(2026, 10, 29, tzinfo=UTC)
        owner, other = uuid4(), uuid4()
        async with factory() as session:
            session.add_all(
                [
                    User(id=owner, email="owner@example.vn", status=UserStatus.ACTIVE),
                    User(id=other, email="other@example.vn", status=UserStatus.ACTIVE),
                ]
            )
            campaign = VoucherCampaign(
                code="WELCOME",
                title="Tri ân",
                description="Cảm ơn bạn",
                terms="Không quy đổi thành tiền mặt",
                image_path="/voucher.webp",
                amount_vnd=200_000,
                validity_days=60,
                active=True,
            )
            session.add(campaign)
            await _seed_recipients(session)
            await session.commit()
            campaign_id = campaign.id
            service = VoucherService(session)
            assert (await service.offer(owner, now=now)).id == campaign_id
            first = await service.claim(owner, campaign_id, now=now)
            again = await service.claim(owner, campaign_id, now=now)
            assert first.id == again.id
            assert first.amount_vnd == 200_000
            assert first.expires_at.replace(tzinfo=UTC) == now + timedelta(days=60)
            assert await service.offer(owner, now=now) is None
            assert await service.mine(other) == []
            assert (await service.offer(other, now=now)).id == campaign_id
            campaign.amount_vnd = 100_000
            campaign.active = False
            await session.commit()
            replay = await service.claim(owner, campaign_id, now=now)
            assert replay.amount_vnd == 200_000
            campaign.active = True
            await session.commit()
            await service.claim(other, campaign_id, now=now)
            assert (
                await session.scalar(select(func.count()).select_from(VoucherClaim))
                == 2
            )
        async with factory() as session:
            saved = await VoucherService(session).mine(owner)
            assert len(saved) == 1 and saved[0].id == first.id
        await engine.dispose()

    asyncio.run(scenario())


def test_migration_seeds_offer_and_preserves_claims_on_downgrade():
    path = (
        Path(__file__).resolve().parents[2] / "alembic/versions/0145_login_vouchers.py"
    )
    spec = importlib.util.spec_from_file_location("login_vouchers_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        User.__table__.create(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            campaign_table = Table(
                "voucher_campaigns", MetaData(), autoload_with=connection
            )
            claim_table = Table("voucher_claims", MetaData(), autoload_with=connection)
            campaign = connection.execute(select(campaign_table)).mappings().one()
            assert campaign["amount_vnd"] == 200_000
            assert campaign["active"] is True
            assert campaign["validity_days"] == 60
            owner = uuid4()
            connection.execute(
                User.__table__.insert().values(id=owner, email="owner@example.vn")
            )
            connection.execute(
                claim_table.insert().values(
                    id=uuid4().hex,
                    user_id=owner.hex,
                    campaign_id=campaign["id"],
                    title="Tri ân",
                    terms="Điều kiện",
                    image_path=campaign["image_path"],
                    amount_vnd=200_000,
                    claimed_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC) + timedelta(days=60),
                )
            )
            with pytest.raises(RuntimeError, match="Preserve claimed vouchers"):
                migration.downgrade()
            assert (
                connection.scalar(select(func.count()).select_from(VoucherClaim)) == 1
            )
            connection.execute(VoucherClaim.__table__.delete())
            migration.downgrade()
            assert "voucher_campaigns" not in inspect(connection).get_table_names()
    engine.dispose()


def test_api_auth_csrf_identity_and_saved_voucher_contract():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: Base.metadata.create_all(
                    c,
                    tables=[
                        User.__table__,
                        Role.__table__, Permission.__table__, UserPermission.__table__, RolePermission.__table__,
                        UserRole.__table__,
                        Department.__table__,
                        Employee.__table__,
                        Notification.__table__,
                        VoucherPresentationState.__table__,
                        VoucherCampaign.__table__,
                        VoucherClaim.__table__,
                    ],
                )
            )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        owner, other, session_id = uuid4(), uuid4(), uuid4()
        async with factory() as session:
            session.add_all(
                [
                    User(id=owner, email="owner@example.vn", status=UserStatus.ACTIVE),
                    User(id=other, email="other@example.vn", status=UserStatus.ACTIVE),
                ]
            )
            campaign = VoucherCampaign(
                code="WELCOME",
                title="Tri ân",
                description="Cảm ơn",
                terms="Điều kiện",
                image_path="/voucher.png",
                amount_vnd=200_000,
                validity_days=60,
                active=True,
            )
            session.add(campaign)
            await _seed_recipients(session)
            await session.commit()
            campaign_id = campaign.id
        app = FastAPI()
        app.include_router(router)
        install_exception_handlers(app)
        settings = Settings(
            auth_csrf_secret=SecretStr("voucher-test-secret-32-characters-long")
        )
        identity = None
        roles = ("USER",)
        is_employee = False

        async def principal():
            if identity is None:
                raise UnauthenticatedError()
            return AuthPrincipal(
                user_id=identity,
                session_id=session_id,
                email="owner@example.vn",
                roles=roles,
            )

        async def session_dependency():
            async with factory() as session:
                yield session

        @app.middleware("http")
        async def request_id(request: Request, call_next):
            request.state.request_id = "voucher-test"
            return await call_next(request)

        app.dependency_overrides[get_current_principal] = principal
        app.dependency_overrides[get_session] = session_dependency
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_employee_profile_link_status] = lambda: is_employee
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for path in ("offer", "mine"):
                assert (await client.get(f"/api/v1/vouchers/{path}")).status_code == 401
            path = f"/api/v1/vouchers/{campaign_id}/claim"
            assert (await client.post(path)).status_code == 401
            identity = owner
            assert (await client.post(path)).status_code == 403
            token = CsrfTokenManager(
                secret=settings.auth_csrf_secret.get_secret_value()
            ).issue(session_id)
            client.cookies.set(settings.auth_csrf_cookie_name, token)
            assert (
                await client.post(path, headers={"X-CSRF-Token": "wrong"})
            ).status_code == 403
            headers = {"X-CSRF-Token": token}
            for account_roles, employee_status in (
                (("SUPER_ADMIN",), False),
                (("USER", "SUPER_ADMIN"), False),
                (("USER", "MODERATOR"), False),
                (("VIEWER",), False),
                ((), False),
                (("USER",), True),
            ):
                roles, is_employee = account_roles, employee_status
                assert (await client.get("/api/v1/vouchers/offer")).json()[
                    "data"
                ] is None
                denied = await client.post(path, headers=headers)
                assert denied.status_code == 403
                assert denied.json()["error"]["code"] == "VOUCHER_NOT_ELIGIBLE"
                assert (await client.get("/api/v1/vouchers/mine")).json()["data"] == []
            roles, is_employee = ("USER",), False
            offer = (await client.get("/api/v1/vouchers/offer")).json()["data"]
            assert offer["amountVnd"] == 200_000 and offer["validityDays"] == 60
            claimed = await client.post(
                path, headers=headers, json={"userId": str(other), "amountVnd": 1}
            )
            assert claimed.status_code == 200
            data = claimed.json()["data"]
            assert data["amountVnd"] == 200_000
            assert data["campaignId"] == str(campaign_id)
            assert "user_id" not in data and "userId" not in data
            assert (await client.post(path, headers=headers)).json()["data"][
                "id"
            ] == data["id"]
            assert (await client.get("/api/v1/vouchers/offer")).json()["data"] is None
            assert len((await client.get("/api/v1/vouchers/mine")).json()["data"]) == 1
            identity = other
            assert (await client.get("/api/v1/vouchers/mine")).json()["data"] == []
        await engine.dispose()

    asyncio.run(scenario())


def test_concurrent_claims_issue_one_voucher(tmp_path):
    async def scenario():
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{tmp_path / 'vouchers.sqlite3'}"
        )
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: Base.metadata.create_all(
                    c,
                    tables=[
                        User.__table__,
                        Role.__table__, Permission.__table__, UserPermission.__table__, RolePermission.__table__,
                        UserRole.__table__,
                        Department.__table__,
                        Employee.__table__,
                        Notification.__table__,
                        VoucherPresentationState.__table__,
                        VoucherCampaign.__table__,
                        VoucherClaim.__table__,
                    ],
                )
            )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        async with factory() as session:
            session.add(
                User(id=user_id, email="owner@example.vn", status=UserStatus.ACTIVE)
            )
            campaign = VoucherCampaign(
                code="WELCOME",
                title="Tri ân",
                description="Cảm ơn",
                terms="Điều kiện",
                image_path="/voucher.png",
                amount_vnd=200_000,
                validity_days=60,
                active=True,
            )
            session.add(campaign)
            await _seed_recipients(session)
            await session.commit()
            campaign_id = campaign.id

        async def claim():
            async with factory() as session:
                return (await VoucherService(session).claim(user_id, campaign_id)).id

        ids = await asyncio.gather(*(claim() for _ in range(4)))
        assert len(set(ids)) == 1
        async with factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(VoucherClaim))
                == 1
            )
        await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize("state", ["inactive", "expired", "future", "missing"])
def test_unavailable_campaign_cannot_be_claimed(state):
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: Base.metadata.create_all(
                    c,
                    tables=[
                        User.__table__,
                        Role.__table__, Permission.__table__, UserPermission.__table__, RolePermission.__table__,
                        UserRole.__table__,
                        Department.__table__,
                        Employee.__table__,
                        Notification.__table__,
                        VoucherPresentationState.__table__,
                        VoucherCampaign.__table__,
                        VoucherClaim.__table__,
                    ],
                )
            )
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            owner = uuid4()
            session.add(
                User(id=owner, email="owner@example.vn", status=UserStatus.ACTIVE)
            )
            now = datetime.now(UTC)
            campaign = VoucherCampaign(
                code="WELCOME",
                title="Tri ân",
                description="Cảm ơn",
                terms="Điều kiện",
                image_path="/voucher.webp",
                amount_vnd=200_000,
                validity_days=60,
                active=state != "inactive",
                starts_at=now + timedelta(days=1) if state == "future" else None,
                ends_at=now if state == "expired" else None,
            )
            session.add(campaign)
            await _seed_recipients(session)
            await session.commit()
            service = VoucherService(session)
            with pytest.raises(DomainError) as error:
                await service.claim(
                    owner, uuid4() if state == "missing" else campaign.id, now=now
                )
            assert error.value.code == "VOUCHER_UNAVAILABLE"
            assert await service.mine(owner) == []
        await engine.dispose()

    asyncio.run(scenario())
