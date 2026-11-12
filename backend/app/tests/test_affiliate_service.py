import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import DomainError
from app.modules.affiliate.models import (
    AffiliateCommission,
    AffiliateCommissionRate,
    AffiliateCommissionRuleSet,
    AffiliateReferralCodeAlias,
)
from app.modules.affiliate.service import AffiliateService
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.wallet.service import FinanceLedger
from app.tests.test_payment_service import ADMIN_ID, _service


async def _assign_role(session, user_id, code: str) -> None:
    role = await session.scalar(select(Role).where(Role.code == code))
    if role is None:
        role = Role(code=code)
        session.add(role)
        await session.flush()
    if await session.get(UserRole, (user_id, role.id)) is None:
        session.add(UserRole(user_id=user_id, role_id=role.id))


async def _seed_rule_set(
    session,
    *,
    enabled: bool = False,
    hold_days: int = 30,
    attribution_window_days: int = 30,
    direct_rate_basis_points: int = 0,
    level2_enabled: bool = False,
    level2_rate_basis_points: int = 0,
) -> AffiliateCommissionRuleSet:
    now = datetime.now(UTC)
    rule_set = AffiliateCommissionRuleSet(
        version_no=1,
        status="PUBLISHED",
        enabled=enabled,
        attribution_window_days=attribution_window_days,
        hold_days=hold_days,
        level2_enabled=level2_enabled,
        level2_rate_basis_points=level2_rate_basis_points,
        effective_from=now - timedelta(seconds=1),
        published_at=now - timedelta(seconds=1),
    )
    session.add(rule_set)
    await session.flush()
    session.add(
        AffiliateCommissionRate(
            rule_set_id=rule_set.id,
            service_code="MEMBERSHIP",
            direct_rate_basis_points=direct_rate_basis_points,
        )
    )
    await session.flush()
    return rule_set


def test_profile_creation_is_idempotent_and_excludes_staff_roles() -> None:
    async def exercise() -> None:
        _, sessions, engine, principal = await _service()
        try:
            async with sessions() as session:
                await _assign_role(session, principal.user_id, "USER")
                await session.commit()

            async with sessions() as session:
                service = AffiliateService(session, affiliate_enabled=True)
                first = await service.ensure_profile(principal.user_id)
                second = await service.ensure_profile(principal.user_id)
                assert first.user_id == second.user_id == principal.user_id
                assert first.referral_code == second.referral_code

            async with sessions() as session:
                await _assign_role(session, principal.user_id, "MODERATOR")
                await session.commit()

            async with sessions() as session:
                with pytest.raises(DomainError) as denied:
                    await AffiliateService(session).ensure_profile(principal.user_id)
                assert denied.value.status_code == 403
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_profile_status_history_orders_changes_with_a_fixed_clock() -> None:
    async def exercise() -> None:
        _, sessions, engine, principal = await _service()
        now = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
        try:
            async with sessions() as session:
                await _assign_role(session, principal.user_id, "USER")
                await session.commit()

            async with sessions() as session:
                service = AffiliateService(session, clock=lambda: now)
                await service.ensure_profile(principal.user_id)
                await service.set_profile_status(
                    user_id=principal.user_id,
                    actor_user_id=ADMIN_ID,
                    profile_status="SUSPENDED",
                    reason="Manual review found suspicious activity.",
                )
                await service.set_profile_status(
                    user_id=principal.user_id,
                    actor_user_id=ADMIN_ID,
                    profile_status="ACTIVE",
                    reason="Review completed; access restored.",
                )

                history = await service.list_profile_status_history(
                    user_id=principal.user_id
                )
                assert [item.status for item in history] == ["ACTIVE", "SUSPENDED"]
                assert history[0].created_at > history[1].created_at
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_referral_click_and_attribution_are_idempotent_and_first_touch_wins() -> None:
    async def exercise() -> None:
        _, sessions, engine, principal = await _service()
        try:
            async with sessions() as session:
                await _assign_role(session, principal.user_id, "USER")
                await _seed_rule_set(session)
                await session.commit()

            async with sessions() as session:
                service = AffiliateService(session, affiliate_enabled=True)
                affiliate = await service.ensure_profile(principal.user_id)
                assert 8 <= len(affiliate.short_referral_code) <= 10
                assert affiliate.short_referral_code.startswith("THV")
                click_id = uuid4()
                click = await service.record_click(
                    referral_code=affiliate.referral_code,
                    event_id=click_id,
                )
                replay = await service.record_click(
                    referral_code=affiliate.referral_code,
                    event_id=click_id,
                )
                assert click.id == replay.id == click_id

            async with sessions() as session:
                second_user_id = uuid4()
                session.add(
                    User(
                        id=second_user_id,
                        email="referred@example.vn",
                        status=UserStatus.ACTIVE,
                    )
                )
                await session.flush()
                await _assign_role(session, second_user_id, "USER")
                await session.commit()

            async with sessions() as session:
                service = AffiliateService(session, affiliate_enabled=True)
                attribution = await service.claim_referral(
                    referred_user_id=second_user_id,
                    referral_code=affiliate.referral_code,
                    click_id=click_id,
                )
                replay = await service.claim_referral(
                    referred_user_id=second_user_id,
                    referral_code=affiliate.referral_code,
                    click_id=click_id,
                )
                assert attribution.id == replay.id
                referrals = await service.list_owned_referrals(
                    user_id=principal.user_id
                )
                assert len(referrals) == 1
                assert referrals[0].id == attribution.id
                assert referrals[0].conversion_count == 0
                assert referrals[0].revenue_minor == 0

                other_user_id = uuid4()
                session.add(
                    User(
                        id=other_user_id,
                        email="other-affiliate@example.vn",
                        status=UserStatus.ACTIVE,
                    )
                )
                await session.flush()
                await _assign_role(session, other_user_id, "USER")
                await session.commit()
                other = await AffiliateService(session).ensure_profile(other_user_id)
                with pytest.raises(DomainError) as denied:
                    await service.claim_referral(
                        referred_user_id=second_user_id,
                        referral_code=other.referral_code,
                    )
                assert denied.value.status_code == 409
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_legacy_referral_code_alias_still_attributes_the_same_profile() -> None:
    async def exercise() -> None:
        _, sessions, engine, principal = await _service()
        try:
            async with sessions() as session:
                await _assign_role(session, principal.user_id, "USER")
                await _seed_rule_set(session)
                await session.commit()

            legacy_code = "THVA1B2C3D4E5F6A7B8C9D0E1F2"
            async with sessions() as session:
                service = AffiliateService(session, affiliate_enabled=True)
                profile = await service.ensure_profile(principal.user_id)
                session.add(
                    AffiliateReferralCodeAlias(
                        code=legacy_code,
                        affiliate_user_id=principal.user_id,
                    )
                )
                await session.commit()

            referred_user_id = uuid4()
            async with sessions() as session:
                session.add(
                    User(
                        id=referred_user_id,
                        email="legacy-referral@example.vn",
                        status=UserStatus.ACTIVE,
                    )
                )
                await session.flush()
                await _assign_role(session, referred_user_id, "USER")
                await session.commit()

            async with sessions() as session:
                service = AffiliateService(session, affiliate_enabled=True)
                click = await service.record_click(
                    referral_code=legacy_code,
                    event_id=uuid4(),
                )
                attribution = await service.claim_referral(
                    referred_user_id=referred_user_id,
                    referral_code=legacy_code,
                    click_id=click.id,
                )
                assert attribution.affiliate_user_id == profile.user_id
                assert attribution.referral_code_snapshot == legacy_code
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_configured_two_level_commissions_are_idempotent_and_capped_at_two() -> None:
    async def exercise() -> None:
        _, sessions, engine, top_level_user = await _service()
        try:
            direct_user_id = uuid4()
            payer_user_id = uuid4()
            async with sessions() as session:
                await _assign_role(session, top_level_user.user_id, "USER")
                for user_id, email in (
                    (direct_user_id, "direct-affiliate@example.vn"),
                    (payer_user_id, "commission-payer@example.vn"),
                ):
                    session.add(
                        User(
                            id=user_id,
                            email=email,
                            status=UserStatus.ACTIVE,
                        )
                    )
                    await session.flush()
                    await _assign_role(session, user_id, "USER")
                await _seed_rule_set(
                    session,
                    enabled=True,
                    direct_rate_basis_points=500,
                    level2_enabled=True,
                    level2_rate_basis_points=100,
                )
                await session.commit()

            async with sessions() as session:
                service = AffiliateService(session, affiliate_enabled=True)
                top_profile = await service.ensure_profile(top_level_user.user_id)
                direct_profile = await service.ensure_profile(direct_user_id)
                await service.claim_referral(
                    referred_user_id=direct_user_id,
                    referral_code=top_profile.short_referral_code,
                )
                await service.claim_referral(
                    referred_user_id=payer_user_id,
                    referral_code=direct_profile.short_referral_code,
                )

            async with sessions() as session:
                service = AffiliateService(
                    session,
                    affiliate_enabled=True,
                    direct_commission_enabled=True,
                )
                direct_commission = await service.record_commission(
                    source_reference="membership:two-level-payment",
                    referred_user_id=payer_user_id,
                    service_code="MEMBERSHIP",
                    amount_minor=100_000,
                )
                assert direct_commission is not None
                assert direct_commission.affiliate_user_id == direct_user_id
                assert direct_commission.commission_level == 1

            async with sessions() as session:
                commissions = list(
                    await session.scalars(
                        select(AffiliateCommission).order_by(
                            AffiliateCommission.commission_level
                        )
                    )
                )
                assert [
                    (row.commission_level, row.affiliate_user_id) for row in commissions
                ] == [
                    (1, direct_user_id),
                    (2, top_level_user.user_id),
                ]
                assert [row.commission_amount_minor for row in commissions] == [
                    5_000,
                    1_000,
                ]

            async with sessions() as session:
                replay = await AffiliateService(
                    session,
                    affiliate_enabled=True,
                    direct_commission_enabled=True,
                ).record_commission(
                    source_reference="membership:two-level-payment",
                    referred_user_id=payer_user_id,
                    service_code="MEMBERSHIP",
                    amount_minor=100_000,
                )
                assert replay is not None
                assert replay.commission_level == 1

            async with sessions() as session:
                commissions = list(await session.scalars(select(AffiliateCommission)))
                assert len(commissions) == 2
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_commission_rules_keep_second_level_off_until_configured() -> None:
    async def exercise() -> None:
        _, sessions, engine, principal = await _service()
        try:
            async with sessions() as session:
                await _seed_rule_set(session)
                await session.commit()
                rule_set = await AffiliateService(session).current_rules()
                assert rule_set is not None
                assert rule_set.rule_set.enabled is False
                assert rule_set.rule_set.level2_enabled is False
                assert rule_set.rule_set.level2_rate_basis_points == 0
                assert all(
                    rate.direct_rate_basis_points == 0 for rate in rule_set.rates
                )
                rule_set.rule_set.level2_enabled = True
                rule_set.rule_set.level2_rate_basis_points = 250
                await session.commit()
                current = await AffiliateService(session).current_rules()
                assert current is not None
                assert current.rule_set.id == rule_set.rule_set.id
                assert current.rule_set.level2_enabled is True
                assert current.rule_set.level2_rate_basis_points == 250
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_rule_versions_are_append_only_and_effective_by_publish_time() -> None:
    async def exercise() -> None:
        _, sessions, engine, _ = await _service()
        now = datetime.now(UTC)
        try:
            async with sessions() as session:
                service = AffiliateService(session, clock=lambda: now)
                first = await service.create_rule_set(
                    actor_user_id=ADMIN_ID,
                    enabled=True,
                    attribution_window_days=60,
                    hold_days=7,
                    rates=(("MEMBERSHIP", 750),),
                )
                assert first.rule_set.version_no == 1
                assert first.rule_set.status == "DRAFT"
                assert await service.current_rules() is None

                published_first = await service.publish_rule_set(
                    actor_user_id=ADMIN_ID,
                    rule_set_id=first.rule_set.id,
                )
                assert published_first.rule_set.status == "PUBLISHED"
                current = await service.current_rules()
                assert current is not None
                assert current.rule_set.version_no == 1
                assert current.rates[0].direct_rate_basis_points == 750

                now = now + timedelta(seconds=1)
                second = await service.create_rule_set(
                    actor_user_id=ADMIN_ID,
                    enabled=True,
                    attribution_window_days=90,
                    hold_days=14,
                    rates=(("MEMBERSHIP", 500),),
                )
                assert second.rule_set.version_no == 2
                await service.publish_rule_set(
                    actor_user_id=ADMIN_ID,
                    rule_set_id=second.rule_set.id,
                )
                latest = await service.current_rules()
                assert latest is not None
                assert latest.rule_set.version_no == 2
                assert latest.rates[0].direct_rate_basis_points == 500
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_affiliate_and_direct_commission_flags_block_source_accrual() -> None:
    async def exercise() -> None:
        _, sessions, engine, principal = await _service()
        try:
            async with sessions() as session:
                disabled = AffiliateService(session)
                assert (
                    await disabled.record_commission(
                        source_reference="membership:feature-off",
                        referred_user_id=principal.user_id,
                        service_code="MEMBERSHIP",
                        amount_minor=100_000,
                    )
                    is None
                )
                direct_disabled = AffiliateService(session, affiliate_enabled=True)
                assert (
                    await direct_disabled.record_commission(
                        source_reference="membership:direct-off",
                        referred_user_id=principal.user_id,
                        service_code="MEMBERSHIP",
                        amount_minor=100_000,
                    )
                    is None
                )
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_signup_attribution_accepts_pending_user_and_locks_first_touch() -> None:
    async def exercise() -> None:
        _, sessions, engine, principal = await _service()
        now = datetime.now(UTC)
        try:
            async with sessions() as session:
                await _assign_role(session, principal.user_id, "USER")
                pending_id = uuid4()
                session.add(
                    User(
                        id=pending_id,
                        email="pending@example.vn",
                        status=UserStatus.PENDING,
                    )
                )
                await session.flush()
                await _assign_role(session, pending_id, "USER")
                await _seed_rule_set(session, attribution_window_days=30)
                await session.commit()

            async with sessions() as session:
                service = AffiliateService(
                    session, affiliate_enabled=True, clock=lambda: now
                )
                referrer = await service.ensure_profile(principal.user_id)
                async with session.begin():
                    attribution = (
                        await service.capture_signup_referral_in_current_transaction(
                            referred_user_id=pending_id,
                            referral_code=referrer.referral_code,
                        )
                    )
                async with session.begin():
                    replay = (
                        await service.capture_signup_referral_in_current_transaction(
                            referred_user_id=pending_id,
                            referral_code=referrer.referral_code,
                        )
                    )
                assert attribution.id == replay.id
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_commission_requires_approval_hold_and_source_safe_reversal() -> None:
    async def exercise() -> None:
        _, sessions, engine, principal = await _service()
        now = [datetime.now(UTC)]
        try:
            async with sessions() as session:
                await _assign_role(session, principal.user_id, "USER")
                referred_id = uuid4()
                session.add(
                    User(
                        id=referred_id,
                        email="commission-source@example.vn",
                        status=UserStatus.ACTIVE,
                    )
                )
                await session.flush()
                await _assign_role(session, referred_id, "USER")
                await _seed_rule_set(
                    session,
                    enabled=True,
                    hold_days=2,
                    attribution_window_days=3650,
                    direct_rate_basis_points=1000,
                )
                await session.commit()

            async with sessions() as session:
                service = AffiliateService(
                    session,
                    affiliate_enabled=True,
                    direct_commission_enabled=True,
                    clock=lambda: now[0],
                )
                referrer = await service.ensure_profile(principal.user_id)
                await service.ensure_profile(referred_id)
                await service.claim_referral(
                    referred_user_id=referred_id,
                    referral_code=referrer.referral_code,
                )
                async with session.begin():
                    commission = await service.record_commission_in_current_transaction(
                        source_reference="membership:test-order-1",
                        referred_user_id=referred_id,
                        service_code="MEMBERSHIP",
                        amount_minor=1_000_000,
                    )
                assert commission is not None
                assert commission.status == "PENDING"
                assert commission.commission_amount_minor == 100_000
                replay = await service.record_commission(
                    source_reference="membership:test-order-1",
                    referred_user_id=referred_id,
                    service_code="MEMBERSHIP",
                    amount_minor=1_000_000,
                )
                assert replay.id == commission.id

                approved = await service.approve_commission(
                    commission_id=commission.id,
                    actor_user_id=ADMIN_ID,
                )
                assert approved.status == "ON_HOLD"
                async with session.begin():
                    available, _ = await FinanceLedger(session).user_accounts(
                        principal.user_id
                    )
                    assert await FinanceLedger(session).balance(available.id) == 0

                now[0] += timedelta(days=3)
                assert await service.release_matured_commissions(limit=10) == 1
                async with session.begin():
                    available, _ = await FinanceLedger(session).user_accounts(
                        principal.user_id
                    )
                    assert await FinanceLedger(session).balance(available.id) == 100_000
                reversed_commission = await service.reverse_commission(
                    commission_id=commission.id,
                    actor_user_id=ADMIN_ID,
                    reason="Customer order was refunded",
                )
                assert reversed_commission.status == "REVERSED"
                async with session.begin():
                    available, _ = await FinanceLedger(session).user_accounts(
                        principal.user_id
                    )
                    assert await FinanceLedger(session).balance(available.id) == 0
                replayed_reversal = await service.reverse_commission(
                    commission_id=commission.id,
                    actor_user_id=ADMIN_ID,
                    reason="Customer order was refunded",
                )
                assert replayed_reversal.id == commission.id
                with pytest.raises(DomainError):
                    await service.record_commission(
                        source_reference="membership:test-order-1",
                        referred_user_id=referred_id,
                        service_code="MEMBERSHIP",
                        amount_minor=2_000_000,
                    )
        finally:
            await engine.dispose()

    asyncio.run(exercise())
