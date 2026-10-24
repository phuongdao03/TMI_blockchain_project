import asyncio
from datetime import UTC, datetime, timedelta
from math import ceil

import pytest
from sqlalchemy import select

from app.main import create_application  # noqa: F401
from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.schemas import CommunityAuthorData
from app.modules.memberships.models import (
    MembershipPlan,
    MembershipPurchase,
    UserMembership,
)
from app.modules.memberships.service import MembershipService
from app.modules.payments.errors import (
    PaymentConflictError,
    PaymentForbiddenError,
)
from app.modules.wallet.models import Wallet, WalletJournal
from app.modules.wallet.service import WalletLedger
from app.tests.test_payment_service import ADMIN_ID, _service


def test_membership_purchase_is_atomic_idempotent_and_expiry_revokes_chat() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                membership = MembershipService(session)
                initial = await membership.overview(owner.user_id)
                assert initial["tier"] == "MEMBER"
                with pytest.raises(PaymentForbiddenError):
                    await membership.publish(
                        owner,
                        name="Thẻ Đồng hành",
                        tier="COMPANION",
                        amount_minor=100_000,
                        duration_days=30,
                    )
                admin = AuthPrincipal(
                    user_id=ADMIN_ID,
                    session_id=owner.session_id,
                    email="admin@example.vn",
                    roles=("SUPER_ADMIN",),
                )
                plan = await membership.publish(
                    admin,
                    name="Thẻ Đồng hành",
                    tier="COMPANION",
                    amount_minor=100_000,
                    duration_days=30,
                )
                plan_id = plan.id
                with pytest.raises(PaymentForbiddenError):
                    await membership.chat(owner, "COMPANION")
                async with session.begin():
                    await WalletLedger(session).post(
                        user_id=owner.user_id,
                        delta=250_000,
                        kind="TOPUP",
                        key="funds",
                        reference="topup:membership",
                        description="Nạp tiền",
                    )
                quote = await membership.quote(owner.user_id, plan_id)
                purchased = await membership.purchase(
                    owner.user_id,
                    plan_id,
                    "buy-companion",
                    expected_amount_minor=quote["amount_due_minor"],
                )
                assert purchased["tier"] == "COMPANION"
                replay = await membership.purchase(
                    owner.user_id,
                    plan_id,
                    "buy-companion",
                    expected_amount_minor=quote["amount_due_minor"],
                )
                assert replay["expires_at"] == purchased["expires_at"]
                messages = await membership.chat(
                    owner, "COMPANION", "Cùng gìn giữ giá trị Việt"
                )
                assert messages[0]["tier"] == "COMPANION"
                assert messages[0]["body"] == "Cùng gìn giữ giá trị Việt"
                async with session.begin():
                    assert await session.scalar(select(Wallet.balance_minor)) == 150_000
                    assert len(list(await session.scalars(select(WalletJournal)))) == 2
                    row = await session.get(UserMembership, owner.user_id)
                    assert row is not None
                    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                with pytest.raises(PaymentForbiddenError):
                    await membership.chat(owner, "COMPANION")
                assert (await membership.overview(owner.user_id))["tier"] == "MEMBER"
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_insufficient_membership_funds_do_not_activate_entitlements() -> None:
    from app.core.errors import DomainError

    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                plan = MembershipPlan(
                    name="Tinh hoa",
                    tier="COMPANION",
                    amount_minor=200_000,
                    duration_days=30,
                )
                async with session.begin():
                    session.add(plan)
                    await session.flush()
                    plan_id = plan.id
                with pytest.raises(DomainError, match="Số dư"):
                    await MembershipService(session).purchase(
                        owner.user_id,
                        plan_id,
                        "insufficient",
                        expected_amount_minor=200_000,
                    )
                async with session.begin():
                    assert await session.get(UserMembership, owner.user_id) is None
                    assert not list(await session.scalars(select(WalletJournal)))
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_upgrade_quote_prorates_credit_and_confirms_amount() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                silver = MembershipPlan(
                    name="Kết nối",
                    tier="SILVER",
                    amount_minor=490_000,
                    duration_days=365,
                )
                gold = MembershipPlan(
                    name="Đồng hành",
                    tier="COMPANION",
                    amount_minor=1_490_000,
                    duration_days=365,
                )
                async with session.begin():
                    session.add_all([silver, gold])
                    await session.flush()
                    silver_id, gold_id = silver.id, gold.id
                expires_at = datetime.now(UTC) + timedelta(days=182)
                async with session.begin():
                    await WalletLedger(session).post(
                        user_id=owner.user_id,
                        delta=2_000_000,
                        kind="TOPUP",
                        key="upgrade-funds",
                        reference="topup:upgrade-test",
                        description="Test funding",
                    )
                    old_payment = await WalletLedger(session).post(
                        user_id=owner.user_id,
                        delta=-490_000,
                        kind="PAYMENT",
                        key="old-silver-purchase",
                        reference="membership:old-silver-purchase",
                        description="Silver membership",
                    )
                    session.add(
                        MembershipPurchase(
                            id=old_payment.id,
                            user_id=owner.user_id,
                            plan_id=silver_id,
                            tier="SILVER",
                            amount_minor=490_000,
                            list_price_minor=490_000,
                            credit_minor=0,
                            expires_at=expires_at,
                        )
                    )
                    session.add(
                        UserMembership(
                            user_id=owner.user_id,
                            plan_id=silver.id,
                            tier="SILVER",
                            expires_at=expires_at,
                        )
                    )

                membership = MembershipService(session)
                quote = await membership.quote(owner.user_id, gold_id)
                assert quote["kind"] == "UPGRADE"
                assert quote["list_price_minor"] == 1_490_000
                assert quote["credit_minor"] == (
                    490_000 * quote["remaining_days"] // 365
                )
                assert quote["amount_due_minor"] == (1_490_000 - quote["credit_minor"])
                with pytest.raises(PaymentConflictError):
                    await membership.purchase(
                        owner.user_id,
                        gold_id,
                        "upgrade-wrong-amount",
                        expected_amount_minor=quote["amount_due_minor"] - 1,
                    )
                purchased = await membership.purchase(
                    owner.user_id,
                    gold_id,
                    "upgrade-confirmed",
                    expected_amount_minor=quote["amount_due_minor"],
                )
                assert purchased["tier"] == "COMPANION"
                replay = await membership.purchase(
                    owner.user_id,
                    gold_id,
                    "upgrade-confirmed",
                    expected_amount_minor=quote["amount_due_minor"],
                )
                assert replay["expires_at"] == purchased["expires_at"]
                async with session.begin():
                    assert await session.scalar(select(Wallet.balance_minor)) == (
                        2_000_000 - 490_000 - quote["amount_due_minor"]
                    )
                    latest_purchase = await session.scalar(
                        select(MembershipPurchase)
                        .where(
                            MembershipPurchase.user_id == owner.user_id,
                            MembershipPurchase.expires_at == purchased["expires_at"],
                        )
                        .order_by(MembershipPurchase.created_at.desc())
                        .limit(1)
                    )
                    assert latest_purchase is not None
                    assert latest_purchase.amount_minor == quote["amount_due_minor"]
                    assert latest_purchase.list_price_minor == 1_490_000
                    assert latest_purchase.credit_minor == quote["credit_minor"]
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_upgrade_quote_credits_all_unexpired_renewal_cycles() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                silver = MembershipPlan(
                    name="Kết nối",
                    tier="SILVER",
                    amount_minor=490_000,
                    duration_days=365,
                )
                gold = MembershipPlan(
                    name="Đồng hành",
                    tier="COMPANION",
                    amount_minor=1_490_000,
                    duration_days=365,
                )
                now = datetime.now(UTC)
                first_expiry = now + timedelta(days=200)
                second_expiry = first_expiry + timedelta(days=365)
                async with session.begin():
                    session.add_all([silver, gold])
                    await session.flush()
                    silver_id, gold_id = silver.id, gold.id
                    await WalletLedger(session).post(
                        user_id=owner.user_id,
                        delta=2_000_000,
                        kind="TOPUP",
                        key="multi-renewal-funds",
                        reference="topup:multi-renewal-test",
                        description="Test funding",
                    )
                    first_posting = await WalletLedger(session).post(
                        user_id=owner.user_id,
                        delta=-490_000,
                        kind="PAYMENT",
                        key="multi-renewal-first",
                        reference="membership:multi-renewal-first",
                        description="Silver membership",
                    )
                    second_posting = await WalletLedger(session).post(
                        user_id=owner.user_id,
                        delta=-490_000,
                        kind="PAYMENT",
                        key="multi-renewal-second",
                        reference="membership:multi-renewal-second",
                        description="Silver renewal",
                    )
                    session.add_all(
                        [
                            MembershipPurchase(
                                id=first_posting.id,
                                user_id=owner.user_id,
                                plan_id=silver_id,
                                tier="SILVER",
                                amount_minor=490_000,
                                list_price_minor=490_000,
                                credit_minor=0,
                                expires_at=first_expiry,
                            ),
                            MembershipPurchase(
                                id=second_posting.id,
                                user_id=owner.user_id,
                                plan_id=silver_id,
                                tier="SILVER",
                                amount_minor=490_000,
                                list_price_minor=490_000,
                                credit_minor=0,
                                expires_at=second_expiry,
                            ),
                            UserMembership(
                                user_id=owner.user_id,
                                plan_id=silver_id,
                                tier="SILVER",
                                expires_at=second_expiry,
                            ),
                        ]
                    )

                quote = await MembershipService(session).quote(owner.user_id, gold_id)
                first_cycle_days = ceil(
                    (first_expiry - datetime.now(UTC)).total_seconds() / 86400
                )
                assert quote["remaining_days"] == first_cycle_days + 365
                assert quote["credit_minor"] == (
                    490_000 * first_cycle_days // 365 + 490_000
                )
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_silver_is_a_supported_community_identity_and_enters_general_chat() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            identity = CommunityAuthorData(
                id=owner.user_id,
                username="silver-member",
                display_name="Silver Member",
                avatar_url=None,
                membership_tier="SILVER",
            )
            assert identity.membership_tier == "SILVER"

            async with sessions() as session:
                plan = MembershipPlan(
                    name="Kết nối",
                    tier="SILVER",
                    amount_minor=490_000,
                    duration_days=365,
                )
                async with session.begin():
                    session.add(plan)
                    await session.flush()
                    session.add(
                        UserMembership(
                            user_id=owner.user_id,
                            plan_id=plan.id,
                            tier="SILVER",
                            expires_at=datetime.now(UTC) + timedelta(days=365),
                        )
                    )
                membership = MembershipService(session)
                messages = await membership.chat(owner, "MEMBER", "Hello")
                assert messages[0]["tier"] == "SILVER"
                with pytest.raises(PaymentForbiddenError):
                    await membership.chat(owner, "COMPANION")
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_same_tier_renewal_requires_opt_in_and_downgrades_are_rejected() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                silver = MembershipPlan(
                    name="Kết nối",
                    tier="SILVER",
                    amount_minor=490_000,
                    duration_days=365,
                )
                gold = MembershipPlan(
                    name="Đồng hành",
                    tier="COMPANION",
                    amount_minor=1_490_000,
                    duration_days=365,
                )
                async with session.begin():
                    session.add_all([silver, gold])
                    await session.flush()
                    silver_id, gold_id = silver.id, gold.id
                    session.add(
                        UserMembership(
                            user_id=owner.user_id,
                            plan_id=gold_id,
                            tier="COMPANION",
                            expires_at=datetime.now(UTC) + timedelta(days=30),
                        )
                    )
                membership = MembershipService(session)
                with pytest.raises(PaymentConflictError):
                    await membership.quote(owner.user_id, gold_id)
                renewal = await membership.quote(
                    owner.user_id, gold_id, renewal_opt_in=True
                )
                assert renewal["kind"] == "RENEWAL"
                assert renewal["amount_due_minor"] == 1_490_000
                assert renewal["expires_at"] > datetime.now(UTC) + timedelta(days=360)
                with pytest.raises(PaymentConflictError):
                    await membership.quote(owner.user_id, silver_id)
                assert gold_id != silver_id
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_diamond_payment_requires_admin_approval() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            admin = AuthPrincipal(
                user_id=ADMIN_ID,
                session_id=owner.session_id,
                email="admin@example.vn",
                roles=("SUPER_ADMIN",),
            )
            async with sessions() as session:
                diamond = MembershipPlan(
                    name="Tinh hoa",
                    tier="PRESTIGE",
                    amount_minor=3_990_000,
                    duration_days=365,
                )
                async with session.begin():
                    session.add(diamond)
                    await session.flush()
                    diamond_id = diamond.id
                    await WalletLedger(session).post(
                        user_id=owner.user_id,
                        delta=5_000_000,
                        kind="TOPUP",
                        key="diamond-funds",
                        reference="topup:diamond-test",
                        description="Test funding",
                    )
                membership = MembershipService(session)
                application = await membership.submit_diamond_application(
                    owner, "I want to join the Diamond community."
                )
                application_id = application.id
                with pytest.raises(PaymentForbiddenError):
                    await membership.purchase(
                        owner.user_id,
                        diamond_id,
                        "diamond-unapproved",
                        expected_amount_minor=3_990_000,
                    )
                reviewed = await membership.review_diamond_application(
                    admin,
                    application_id,
                    decision="APPROVED",
                    note="Approved for membership purchase.",
                )
                assert reviewed.status == "APPROVED"
                purchased = await membership.purchase(
                    owner.user_id,
                    diamond_id,
                    "diamond-approved",
                    expected_amount_minor=3_990_000,
                )
                assert purchased["tier"] == "PRESTIGE"
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
