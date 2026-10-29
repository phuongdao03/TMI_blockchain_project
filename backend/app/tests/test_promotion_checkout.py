import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.main import create_application  # noqa: F401
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.promotions.checkout import PromotionCheckout
from app.modules.promotions.checkout_models import VoucherAdjustment, VoucherReservation
from app.modules.promotions.models import VoucherCampaign, VoucherClaim
from app.modules.promotions.schemas import PromotionPolicy

NOW = datetime(2026, 10, 29, tzinfo=UTC)


async def setup(*, budget=300_000, restore=True):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user, other, campaign_id = uuid4(), uuid4(), uuid4()
    policy = PromotionPolicy(
        service_codes=["MEMBERSHIP"], budget_vnd=budget, restore_on_refund=restore
    )
    snapshot = policy.model_dump(mode="json", by_alias=False)
    async with factory() as session:
        role = Role(id=uuid4(), code="USER")
        session.add(role)
        for identifier, email in [(user, "one@example.vn"), (other, "two@example.vn")]:
            session.add(User(id=identifier, email=email, status=UserStatus.ACTIVE))
            session.add(UserRole(user_id=identifier, role_id=role.id))
        campaign = VoucherCampaign(
            id=campaign_id,
            code="CHECKOUT",
            name="Test",
            title="Gift",
            description="Gift",
            terms="Terms",
            image_path="/voucher.png",
            amount_vnd=200_000,
            validity_days=60,
            status="ACTIVE",
            active=True,
            policy_json=snapshot,
        )
        session.add(campaign)
        claim = VoucherClaim(
            id=uuid4(),
            user_id=user,
            campaign_id=campaign_id,
            title="Gift",
            terms="Terms",
            image_path="/voucher.png",
            amount_vnd=200_000,
            claimed_at=NOW,
            expires_at=NOW + timedelta(days=60),
            policy_json=snapshot,
            status="AVAILABLE",
            unique_code="ONE",
        )
        second = VoucherClaim(
            id=uuid4(),
            user_id=other,
            campaign_id=campaign_id,
            title="Gift",
            terms="Terms",
            image_path="/voucher.png",
            amount_vnd=200_000,
            claimed_at=NOW,
            expires_at=NOW + timedelta(days=60),
            policy_json=snapshot,
            status="AVAILABLE",
            unique_code="TWO",
        )
        session.add_all([claim, second])
        await session.commit()
    return engine, factory, user, other, campaign_id, claim.id, second.id


def test_reserve_redeem_refund_are_idempotent_and_budget_balanced():
    async def scenario():
        engine, factory, user, _, campaign_id, voucher_id, _ = await setup()
        async with factory() as session:
            async with session.begin():
                checkout = PromotionCheckout(session, now=NOW)
                row = await checkout.reserve(
                    user,
                    voucher_id,
                    order_reference="membership:one",
                    service_code="MEMBERSHIP",
                    original_vnd=500_000,
                    expires_at=NOW + timedelta(minutes=15),
                )
                replay = await checkout.reserve(
                    user,
                    voucher_id,
                    order_reference="membership:one",
                    service_code="MEMBERSHIP",
                    original_vnd=500_000,
                    expires_at=NOW + timedelta(minutes=15),
                )
                assert replay.id == row.id and row.payable_vnd == 300_000
                assert (
                    await session.get(VoucherCampaign, campaign_id)
                ).budget_reserved_vnd == 200_000
            async with session.begin():
                # TTL alone cannot give a potentially paid voucher to another order.
                late = PromotionCheckout(session, now=NOW + timedelta(hours=1))
                await late.release(
                    "membership:one", reason="Provider timeout", definitive=False
                )
                assert (
                    await session.get(VoucherClaim, voucher_id)
                ).status == "RESERVED"
                await late.redeem("membership:one")
                await late.redeem("membership:one")
                campaign = await session.get(VoucherCampaign, campaign_id)
                assert (
                    campaign.budget_reserved_vnd == 0
                    and campaign.budget_spent_vnd == 200_000
                )
                assert (await session.get(VoucherClaim, voucher_id)).uses_used == 1
            async with session.begin():
                checkout = PromotionCheckout(session, now=NOW)
                await checkout.refund(
                    "membership:one", refund_reference="refund-part", refund_vnd=150_000
                )
                assert (
                    await session.get(VoucherCampaign, campaign_id)
                ).budget_spent_vnd == 100_000
                await checkout.refund(
                    "membership:one", refund_reference="refund-part", refund_vnd=150_000
                )
                await checkout.refund("membership:one", refund_reference="refund-rest")
                assert (
                    await session.get(VoucherCampaign, campaign_id)
                ).budget_spent_vnd == 0
                assert (
                    await session.get(VoucherClaim, voucher_id)
                ).status == "AVAILABLE"
                assert (
                    await session.scalar(
                        select(func.count()).select_from(VoucherReservation)
                    )
                    == 1
                )
                assert (
                    await session.scalar(
                        select(func.count()).select_from(VoucherAdjustment)
                    )
                    == 2
                )
        await engine.dispose()

    asyncio.run(scenario())


def test_other_owner_and_budget_contention_are_rejected():
    async def scenario():
        engine, factory, user, other, _, voucher_id, second_id = await setup(
            budget=200_000
        )
        async with factory() as session:
            async with session.begin():
                checkout = PromotionCheckout(session, now=NOW)
                with pytest.raises(DomainError) as error:
                    await checkout.reserve(
                        other,
                        voucher_id,
                        order_reference="stolen",
                        service_code="MEMBERSHIP",
                        original_vnd=500_000,
                        expires_at=NOW + timedelta(minutes=15),
                    )
                assert error.value.code == "VOUCHER_NOT_FOUND"
                await checkout.reserve(
                    user,
                    voucher_id,
                    order_reference="one",
                    service_code="MEMBERSHIP",
                    original_vnd=500_000,
                    expires_at=NOW + timedelta(minutes=15),
                )
                with pytest.raises(DomainError) as error:
                    await checkout.reserve(
                        other,
                        second_id,
                        order_reference="two",
                        service_code="MEMBERSHIP",
                        original_vnd=500_000,
                        expires_at=NOW + timedelta(minutes=15),
                    )
                assert error.value.code == "VOUCHER_BUDGET_EXHAUSTED"
                with pytest.raises(DomainError) as error:
                    await checkout.reserve(
                        user,
                        voucher_id,
                        order_reference="duplicate",
                        service_code="MEMBERSHIP",
                        original_vnd=500_000,
                        expires_at=NOW + timedelta(minutes=15),
                    )
                assert error.value.code == "VOUCHER_NOT_AVAILABLE"
                await checkout.release("one", reason="Confirmed cancellation")
                await checkout.release("one", reason="Retry cancellation")
                await checkout.reserve(
                    other,
                    second_id,
                    order_reference="two",
                    service_code="MEMBERSHIP",
                    original_vnd=500_000,
                    expires_at=NOW + timedelta(minutes=15),
                )
        await engine.dispose()

    asyncio.run(scenario())


def test_zero_price_membership_purchase_preserves_foreign_keys_and_replay():
    async def scenario():
        from sqlalchemy import text

        from app.modules.memberships.models import MembershipPlan, MembershipPurchase
        from app.modules.memberships.service import MembershipService
        from app.modules.payments.errors import PaymentConflictError
        from app.modules.wallet.models import WalletJournal

        engine, factory, user, _, _, voucher_id, _ = await setup()
        async with factory() as session:
            plan = MembershipPlan(
                name="Companion",
                tier="COMPANION",
                amount_minor=100_000,
                duration_days=30,
            )
            session.add(plan)
            claim = await session.get(VoucherClaim, voucher_id)
            claim.expires_at = datetime.now(UTC) + timedelta(days=60)
            await session.commit()
            plan_id = plan.id
            await session.execute(text("PRAGMA foreign_keys=ON"))
            await session.commit()
            service = MembershipService(session)
            await service.purchase(
                user,
                plan_id,
                "free-member",
                expected_amount_minor=0,
                voucher_id=voucher_id,
            )
            await service.purchase(
                user,
                plan_id,
                "free-member",
                expected_amount_minor=0,
                voucher_id=voucher_id,
            )
            with pytest.raises(PaymentConflictError):
                await service.purchase(
                    user, plan_id, "free-member", expected_amount_minor=0
                )
            purchases = list(await session.scalars(select(MembershipPurchase)))
            assert len(purchases) == 1
            assert (
                purchases[0].amount_minor == 0
                and purchases[0].wallet_journal_id is None
            )
            assert (
                await session.scalar(select(func.count()).select_from(WalletJournal))
                == 0
            )
            assert (await session.get(VoucherClaim, voucher_id)).status == "REDEEMED"
            assert not (await session.execute(text("PRAGMA foreign_key_check"))).all()
        await engine.dispose()

    asyncio.run(scenario())


def test_report_export_contains_all_transactions_and_date_filter():
    async def scenario():
        import csv
        from io import StringIO

        from app.api.v1.admin_promotions import transaction_csv
        from app.modules.promotions.reporting import analytics

        engine, factory, user, _, campaign_id, voucher_id, _ = await setup()
        async with factory() as session:
            for index in range(125):
                session.add(
                    VoucherReservation(
                        voucher_id=voucher_id,
                        campaign_id=campaign_id,
                        user_id=user,
                        order_reference=f"history:{index}",
                        service_code="MEMBERSHIP",
                        status="RELEASED",
                        original_vnd=500000,
                        discount_vnd=200000,
                        payable_vnd=300000,
                        expires_at=NOW,
                        created_at=NOW,
                    )
                )
            await session.commit()
            first = await analytics(session, campaign_id)
            assert (
                len(first["transactions"]) == 100 and first["transactionCount"] == 125
            )
            all_rows = await analytics(session, campaign_id, transaction_limit=None)
            response = transaction_csv(all_rows)
            rows = list(csv.DictReader(StringIO(response.body.decode("utf-8-sig"))))
            assert len(rows) == 125 and rows[0]["orderId"].startswith("history:")
            assert "revenueVnd" in rows[0] and "redeemedAt" in rows[0]
            filtered = await analytics(session, campaign_id, NOW + timedelta(days=1))
            assert filtered["transactionCount"] == 0 and filtered["transactions"] == []
        await engine.dispose()

    asyncio.run(scenario())
