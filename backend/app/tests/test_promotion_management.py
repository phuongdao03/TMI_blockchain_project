import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import main as application_models  # noqa: F401
from app.core.errors import DomainError
from app.db.base import Base
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.promotions.admin_service import (
    CampaignService,
    campaign_data,
    campaign_transition,
)
from app.modules.promotions.models import VoucherClaim
from app.modules.promotions.schemas import CampaignInput, PromotionPolicy
from app.modules.promotions.service import VoucherService


def test_campaign_is_draft_and_requires_explicit_publish():
    assert campaign_transition("DRAFT", "publish", scheduled=False) == "ACTIVE"
    assert campaign_transition("DRAFT", "publish", scheduled=True) == "SCHEDULED"
    assert campaign_transition("ACTIVE", "pause", scheduled=False) == "PAUSED"
    with pytest.raises(DomainError):
        campaign_transition("ARCHIVED", "publish", scheduled=False)


@pytest.mark.parametrize(
    "policy",
    [
        {"discountType": "PERCENT", "percentageBps": 0},
        {"percentageBps": 10001},
        {"minimumOrderVnd": 10, "maximumOrderVnd": 9},
        {"firstOrderOnly": True, "subsequentOrderOnly": True},
        {"serviceCodes": ["WALLET_TOPUP"]},
        {"presentation": {"ctaColor": "javascript:alert(1)"}},
    ],
)
def test_policy_rejects_unsafe_or_incoherent_configuration(policy):
    with pytest.raises(ValidationError):
        PromotionPolicy.model_validate(policy)


def test_builder_rejects_arbitrary_remote_or_script_images():
    with pytest.raises(ValidationError):
        CampaignInput(
            code="TEST",
            name="Test",
            title="Test",
            description="Test",
            terms="Terms",
            imagePath="javascript:alert(1)",
        )


def test_campaign_admin_publishes_issues_and_preserves_historical_policy():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            owner, admin = uuid4(), uuid4()
            role = Role(id=uuid4(), code="USER")
            session.add_all(
                [
                    role,
                    User(id=owner, email="owner@example.vn", status=UserStatus.ACTIVE),
                    User(id=admin, email="admin@example.vn", status=UserStatus.ACTIVE),
                ]
            )
            await session.flush()
            session.add(UserRole(user_id=owner, role_id=role.id))
            await session.commit()
            payload = CampaignInput(
                code="TEST_ADMIN",
                name="Welcome",
                title="Welcome gift",
                description="Thank you",
                terms="Service discount",
                policy=PromotionPolicy(vouchers_per_user=3),
            )
            manager = CampaignService(session)
            row = await manager.save(payload, admin)
            campaign_id = row.id
            assert row.status == "DRAFT" and row.image_path.startswith("/images/")
            assert campaign_data(row).model_dump()["policy"]["vouchersPerUser"] == 3
            await manager.transition(row.id, "publish", admin)
            claim = await VoucherService(session).claim(owner, row.id)
            assert claim.amount_vnd == 200000
            assert len(await VoucherService(session).mine(owner)) == 3
            await VoucherService(session).claim(owner, row.id)
            assert (
                await session.scalar(select(func.count()).select_from(VoucherClaim))
                == 3
            )
            old_policy = dict(claim.policy_json)
            payload.policy.minimum_order_vnd = 1000
            updated = await manager.save(
                payload.model_copy(update={"amount_vnd": 100000}), admin, row.id
            )
            assert updated.status == "ACTIVE"
            assert updated.policy_version == 2
            await session.refresh(claim)
            assert claim.amount_vnd == 200000
            assert claim.policy_json == old_policy
            assert claim.policy_version == 1
            newcomer = uuid4()
            session.add(
                User(id=newcomer, email="new@example.vn", status=UserStatus.ACTIVE)
            )
            await session.flush()
            session.add(UserRole(user_id=newcomer, role_id=role.id))
            await session.commit()
            new_claim = await VoucherService(session).claim(newcomer, campaign_id)
            assert new_claim.amount_vnd == 100000
            assert new_claim.policy_json["minimum_order_vnd"] == 1000
            assert new_claim.policy_version == 2
            row = await manager.required(campaign_id)
            copied = await manager.copy(row.id, admin)
            assert copied.status == "DRAFT" and copied.code != row.code
            # Publishing a manual campaign alone does not grant anything, but
            # its recipients must see the popup after actual distribution.
            manual = await manager.save(
                payload.model_copy(
                    update={"code": "MANUAL_TEST", "program_type": "MANUAL"}
                ),
                admin,
            )
            await manager.transition(manual.id, "publish", admin)
            service = VoucherService(session)
            assert await service.offer(owner) is None
            await service.issue(owner, manual.id, reason="manual distribution")
            assert (await service.offer(owner)).id == manual.id
        await engine.dispose()

    asyncio.run(scenario())


def test_campaign_rejects_empty_registration_interval_on_save_and_publish():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            admin = uuid4()
            session.add(
                User(id=admin, email="dates@example.vn", status=UserStatus.ACTIVE)
            )
            await session.commit()
            manager = CampaignService(session)
            payload = CampaignInput(
                code="DATES",
                name="Dates",
                title="Gift",
                description="Gift",
                terms="Terms",
            )
            campaign = await manager.save(payload, admin)
            point = datetime(2026, 8, 1, tzinfo=UTC)
            payload.policy.audience.registered_after = point
            payload.policy.audience.registered_before = point
            with pytest.raises(DomainError) as error:
                await manager.save(payload, admin, campaign.id)
            assert error.value.code == "PROMOTION_AUDIENCE_PERIOD_INVALID"
            # Old campaigns with invalid intervals remain readable for repair.
            campaign.policy_json = payload.policy.model_dump(
                mode="json", by_alias=False
            )
            await session.commit()
            with pytest.raises(DomainError) as error:
                await manager.transition(campaign.id, "publish", admin)
            assert error.value.code == "PROMOTION_AUDIENCE_PERIOD_INVALID"
        await engine.dispose()

    asyncio.run(scenario())


def test_automatic_issue_survives_dismiss_and_frequency_is_backend_owned():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            user_id = uuid4()
            role = Role(id=uuid4(), code="USER")
            session.add_all(
                [
                    role,
                    User(id=user_id, email="user@example.vn", status=UserStatus.ACTIVE),
                ]
            )
            await session.flush()
            session.add(UserRole(user_id=user_id, role_id=role.id))
            await session.commit()
            policy = PromotionPolicy()
            policy.presentation.frequency = "ONCE"
            policy.presentation.trigger = "DASHBOARD"
            manager = CampaignService(session)
            campaign = await manager.save(
                CampaignInput(
                    code="AUTO_WELCOME",
                    name="Welcome",
                    title="Welcome",
                    description="Hello",
                    terms="Service discount",
                    program_type="AUTO",
                    policy=policy,
                ),
                user_id,
            )
            campaign = await manager.transition(campaign.id, "publish", user_id)
            campaign_id = campaign.id
            session_id = uuid4()
            service = VoucherService(session)
            assert await service.offer(user_id, session_id=session_id) is None
            assert (
                await service.offer(user_id, session_id=session_id, trigger="DASHBOARD")
            ).id == campaign_id
            await service.presentation_event(user_id, campaign_id, session_id, "SEEN")
            await service.presentation_event(
                user_id, campaign_id, session_id, "DISMISSED"
            )
            assert len(await service.mine(user_id)) == 1
        async with factory() as session:
            service = VoucherService(session)
            assert await service.offer(user_id, session_id=uuid4()) is None
            assert len(await service.mine(user_id)) == 1
        await engine.dispose()

    asyncio.run(scenario())


def test_auto_bundle_is_atomic_when_global_issuance_limit_is_too_small():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            user_id = uuid4()
            role = Role(id=uuid4(), code="USER")
            session.add_all(
                [
                    role,
                    User(
                        id=user_id, email="bundle@example.vn", status=UserStatus.ACTIVE
                    ),
                ]
            )
            await session.flush()
            session.add(UserRole(user_id=user_id, role_id=role.id))
            await session.commit()
            campaign = await CampaignService(session).save(
                CampaignInput(
                    code="ATOMIC_AUTO",
                    name="Atomic",
                    title="Atomic",
                    description="Atomic",
                    terms="Terms",
                    program_type="AUTO",
                    policy=PromotionPolicy(vouchers_per_user=3, issuance_limit=2),
                ),
                user_id,
            )
            await CampaignService(session).transition(campaign.id, "publish", user_id)
            assert (
                await VoucherService(session).offer(user_id, session_id=uuid4()) is None
            )
            assert len(await VoucherService(session).mine(user_id)) == 0
        await engine.dispose()

    asyncio.run(scenario())


def test_first_order_program_enforces_first_order_policy():
    payload = CampaignInput(
        code="FIRST_GIFT",
        name="First",
        title="First",
        description="Gift",
        terms="Terms",
        program_type="FIRST_ORDER",
    )
    assert payload.policy.first_order_only
    with pytest.raises(ValueError):
        CampaignInput(
            code="FIRST_GIFT",
            name="First",
            title="First",
            description="Gift",
            terms="Terms",
            program_type="FIRST_ORDER",
            policy=PromotionPolicy(subsequent_order_only=True),
        )
