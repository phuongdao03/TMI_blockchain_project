import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.events.models import (
    CommunityEvent,
    CommunityEventRegistration,
    MembershipEventEntitlementPolicy,
    MembershipEventEntitlementUsage,
)
from app.modules.events.service import CommunityEventService
from app.modules.memberships.models import (
    MembershipDiamondApplication,
    MembershipPlan,
    UserMembership,
)
from app.modules.notifications.models import Notification
from app.modules.wallet.models import WalletJournal
from app.tests.test_payment_service import ADMIN_ID, _service


def _admin(owner: AuthPrincipal) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=ADMIN_ID,
        session_id=owner.session_id,
        email="admin@example.vn",
        roles=("SUPER_ADMIN",),
    )


def test_community_event_routes_are_registered() -> None:
    from app.main import app

    paths = app.openapi()["paths"]
    assert "/api/v1/events" in paths
    assert "/api/v1/events/{event_id}/registrations" in paths
    assert "/api/v1/events/me/registrations" in paths
    assert "/api/v1/admin/events" in paths
    assert "/api/v1/admin/events/{event_id}/publish" in paths
    assert "/api/v1/admin/events/{event_id}/cancel" in paths


def test_event_admin_lifecycle_public_listing_and_paid_registration_gate() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                service = CommunityEventService(session)
                admin = _admin(owner)
                starts = datetime.now(UTC) + timedelta(days=4)
                draft = await service.create(
                    admin,
                    title="Tinh hoa kết nối",
                    description="Gặp gỡ hội viên.",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=2),
                    location="Hà Nội",
                    required_tier="SILVER",
                    capacity=4,
                    ticket_price_minor=0,
                    cancellation_cutoff_at=starts - timedelta(days=1),
                    included_entitlement="TALK",
                    entitlement_quota=2,
                    requires_diamond_approval=False,
                )
                assert (await service.list_public(page=1, page_size=20))[1] == 0
                published = await service.publish(admin, draft.id)
                assert published.status == "PUBLISHED"
                assert (await service.list_public(page=1, page_size=20))[1] == 1

                paid = await service.create(
                    admin,
                    title="Sự kiện có phí",
                    description="Chưa bật thanh toán vé.",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=2),
                    location="Hà Nội",
                    required_tier="MEMBER",
                    capacity=2,
                    ticket_price_minor=250_000,
                    cancellation_cutoff_at=None,
                    included_entitlement=None,
                    entitlement_quota=None,
                    requires_diamond_approval=False,
                )
                await service.publish(admin, paid.id)
                with pytest.raises(DomainError) as error:
                    await service.register(owner, paid.id)
                assert error.value.status_code == 402
                assert error.value.code == "PAYMENT_REQUIRED"
                async with session.begin():
                    assert (
                        await session.scalar(
                            select(func.count()).select_from(CommunityEventRegistration)
                        )
                        == 0
                    )
                    assert (
                        await session.scalar(
                            select(func.count()).select_from(WalletJournal)
                        )
                        == 0
                    )
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_event_capacity_waitlist_promotion_and_entitlement_restoration_policy() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        second = uuid4()
        third = uuid4()
        try:
            async with sessions() as session:
                from app.modules.auth.models import User, UserStatus

                async with session.begin():
                    silver = MembershipPlan(
                        name="Káº¿t ná»‘i",
                        tier="SILVER",
                        amount_minor=490_000,
                        duration_days=365,
                    )
                    session.add(silver)
                    await session.flush()
                    session.add_all(
                        [
                            User(
                                id=second,
                                email="second@example.vn",
                                status=UserStatus.ACTIVE,
                            ),
                            User(
                                id=third,
                                email="third@example.vn",
                                status=UserStatus.ACTIVE,
                            ),
                        ]
                    )
                    for member_id in (owner.user_id, second, third):
                        session.add(
                            UserMembership(
                                user_id=member_id,
                                plan_id=silver.id,
                                tier="SILVER",
                                expires_at=datetime.now(UTC) + timedelta(days=365),
                            )
                        )
                    session.add(
                        MembershipEventEntitlementPolicy(
                            tier="SILVER", entitlement="TALK", quota_count=1
                        )
                    )
                service = CommunityEventService(session)
                admin = _admin(owner)
                starts = datetime.now(UTC) + timedelta(days=5)
                event = await service.create(
                    admin,
                    title="Talk nhỏ",
                    description="Chỗ ngồi giới hạn.",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=1),
                    location="TP.HCM",
                    required_tier="SILVER",
                    capacity=1,
                    ticket_price_minor=0,
                    cancellation_cutoff_at=starts - timedelta(days=1),
                    included_entitlement="TALK",
                    entitlement_quota=1,
                    requires_diamond_approval=False,
                )
                event_id = event.id
                await service.publish(admin, event_id)
                one = await service.register(owner, event_id)
                owner_cycle = one.entitlement_cycle_started_at
                two_principal = AuthPrincipal(
                    second, owner.session_id, "second@example.vn", ()
                )
                two = await service.register(two_principal, event_id)
                assert one.status == "CONFIRMED"
                assert two.status == "WAITLISTED"
                assert await service.register(two_principal, event.id) == two

                await service.cancel_registration(owner, event_id)
                async with session.begin():
                    one_after = await session.get(CommunityEventRegistration, one.id)
                    assert one_after is not None and one_after.status == "CANCELLED"
                    owner_usage = await session.get(
                        MembershipEventEntitlementUsage,
                        (
                            owner.user_id,
                            "SILVER",
                            "TALK",
                            owner_cycle,
                        ),
                    )
                    assert owner_usage is not None and owner_usage.used_count == 0
                    two_after = await session.get(CommunityEventRegistration, two.id)
                    assert two_after is not None and two_after.status == "CONFIRMED"
                    two_cycle = two_after.entitlement_cycle_started_at
                    assert two_cycle is not None
                    stored_event = await session.get(CommunityEvent, event_id)
                    assert (
                        stored_event is not None and stored_event.confirmed_count == 1
                    )

                third_principal = AuthPrincipal(
                    third, owner.session_id, "third@example.vn", ()
                )
                three = await service.register(third_principal, event_id)
                assert three.status == "WAITLISTED"

                # Late cancellation keeps the member's yearly quota consumed.
                async with session.begin():
                    stored_event = await session.get(CommunityEvent, event_id)
                    assert stored_event is not None
                    stored_event.cancellation_cutoff_at = datetime.now(UTC) - timedelta(
                        seconds=1
                    )
                await service.cancel_registration(two_principal, event_id)
                assert await service.register(third_principal, event_id) == three
                async with session.begin():
                    stored_event = await session.get(CommunityEvent, event_id)
                    three_after = await session.get(
                        CommunityEventRegistration, three.id
                    )
                    second_usage = await session.get(
                        MembershipEventEntitlementUsage,
                        (
                            second,
                            "SILVER",
                            "TALK",
                            two_cycle,
                        ),
                    )
                    assert (
                        stored_event is not None and stored_event.confirmed_count == 1
                    )
                    assert three_after is not None and three_after.status == "CONFIRMED"
                    assert second_usage is not None and second_usage.used_count == 1

                second_free_event = await service.create(
                    admin,
                    title="Talk tiáº¿p theo",
                    description="KhÃ´ng cÃ²n lÆ°á»£t miá»…n phÃ­.",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=1),
                    location="TP.HCM",
                    required_tier="SILVER",
                    capacity=4,
                    ticket_price_minor=0,
                    cancellation_cutoff_at=None,
                    included_entitlement="TALK",
                    entitlement_quota=1,
                    requires_diamond_approval=False,
                )
                second_free_event_id = second_free_event.id
                await service.publish(admin, second_free_event_id)
                with pytest.raises(DomainError) as quota_error:
                    await service.register(two_principal, second_free_event_id)
                assert quota_error.value.code == "EVENT_ENTITLEMENT_QUOTA_EXHAUSTED"

                paid_event = await service.create(
                    admin,
                    title="Talk cÃ³ phÃ­",
                    description="Mua vÃ© khi háº¿t lÆ°á»£t miá»…n phÃ­.",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=1),
                    location="TP.HCM",
                    required_tier="SILVER",
                    capacity=4,
                    ticket_price_minor=250_000,
                    cancellation_cutoff_at=None,
                    included_entitlement="TALK",
                    entitlement_quota=1,
                    requires_diamond_approval=False,
                )
                paid_event_id = paid_event.id
                await service.publish(admin, paid_event_id)
                with pytest.raises(DomainError) as payment_error:
                    await service.register(two_principal, paid_event_id)
                assert payment_error.value.code == "PAYMENT_REQUIRED"
                assert payment_error.value.status_code == 402

                paid_waitlist_event = await service.create(
                    admin,
                    title="Talk chuyển phí",
                    description="Sự kiện đổi giá khi đang có danh sách chờ.",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=1),
                    location="TP.HCM",
                    required_tier="SILVER",
                    capacity=1,
                    ticket_price_minor=0,
                    cancellation_cutoff_at=None,
                    included_entitlement=None,
                    entitlement_quota=None,
                    requires_diamond_approval=False,
                )
                paid_waitlist_event_id = paid_waitlist_event.id
                await service.publish(admin, paid_waitlist_event_id)
                paid_waitlist_owner = await service.register(
                    owner, paid_waitlist_event_id
                )
                paid_waiter = await service.register(
                    two_principal, paid_waitlist_event_id
                )
                assert paid_waitlist_owner.status == "CONFIRMED"
                assert paid_waiter.status == "WAITLISTED"
                await service.update(
                    admin, paid_waitlist_event_id, ticket_price_minor=250_000
                )
                await service.cancel_registration(owner, paid_waitlist_event_id)
                async with session.begin():
                    paid_waiter_after = await session.get(
                        CommunityEventRegistration, paid_waiter.id
                    )
                    paid_waitlist_stored_event = await session.get(
                        CommunityEvent, paid_waitlist_event_id
                    )
                    assert (
                        paid_waiter_after is not None
                        and paid_waiter_after.status == "PAYMENT_REQUIRED"
                    )
                    assert (
                        paid_waitlist_stored_event is not None
                        and paid_waitlist_stored_event.confirmed_count == 0
                    )

                await service.cancel_event(admin, event_id)
                async with session.begin():
                    second_usage = await session.get(
                        MembershipEventEntitlementUsage,
                        (
                            second,
                            "SILVER",
                            "TALK",
                            two_cycle,
                        ),
                    )
                    assert second_usage is not None and second_usage.used_count == 0
                restored_registration = await service.register(
                    two_principal, second_free_event_id
                )
                assert restored_registration.status == "CONFIRMED"
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_priority_registration_window_and_tier_matched_notifications() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        second = uuid4()
        try:
            async with sessions() as session:
                from app.modules.auth.models import User, UserStatus

                now = datetime.now(UTC)
                async with session.begin():
                    silver = MembershipPlan(
                        name="Silver",
                        tier="SILVER",
                        amount_minor=490_000,
                        duration_days=365,
                    )
                    companion = MembershipPlan(
                        name="Companion",
                        tier="COMPANION",
                        amount_minor=1_490_000,
                        duration_days=365,
                    )
                    session.add_all([silver, companion])
                    await session.flush()
                    session.add(
                        User(
                            id=second,
                            email="silver@example.vn",
                            status=UserStatus.ACTIVE,
                        )
                    )
                    session.add_all(
                        [
                            UserMembership(
                                user_id=owner.user_id,
                                plan_id=companion.id,
                                tier="COMPANION",
                                expires_at=now + timedelta(days=365),
                            ),
                            UserMembership(
                                user_id=second,
                                plan_id=silver.id,
                                tier="SILVER",
                                expires_at=now + timedelta(days=365),
                            ),
                        ]
                    )

                service = CommunityEventService(session)
                admin = _admin(owner)
                starts = now + timedelta(days=2)
                event = await service.create(
                    admin,
                    title="Tinh Hoa Connect",
                    description="Kết nối hội viên theo lĩnh vực.",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=2),
                    registration_opens_at=now + timedelta(hours=1),
                    priority_tier="COMPANION",
                    priority_opens_at=now - timedelta(hours=2),
                    location="Hà Nội",
                    required_tier="SILVER",
                    capacity=3,
                    ticket_price_minor=0,
                    cancellation_cutoff_at=None,
                    included_entitlement=None,
                    entitlement_quota=None,
                    requires_diamond_approval=False,
                )
                event_id = event.id
                await service.publish(admin, event_id)
                notices = list(
                    await session.scalars(
                        select(Notification).where(
                            Notification.source_event_id == event_id
                        )
                    )
                )
                assert {notice.user_id for notice in notices} == {owner.user_id, second}
                await session.commit()

                priority_registration = await service.register(owner, event_id)
                assert priority_registration.status == "CONFIRMED"
                silver_member = AuthPrincipal(
                    user_id=second,
                    session_id=owner.session_id,
                    email="silver@example.vn",
                    roles=(),
                )
                with pytest.raises(DomainError) as error:
                    await service.register(silver_member, event_id)
                assert error.value.code == "EVENT_REGISTRATION_NOT_OPEN"

                await service.update(
                    admin, event_id, registration_opens_at=now - timedelta(hours=1)
                )
                general_registration = await service.register(silver_member, event_id)
                assert general_registration.status == "CONFIRMED"
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_diamond_circle_requires_current_prestige_and_approved_application() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                plan = MembershipPlan(
                    name="Tinh hoa",
                    tier="PRESTIGE",
                    amount_minor=3_990_000,
                    duration_days=365,
                )
                starts = datetime.now(UTC) + timedelta(days=8)
                async with session.begin():
                    session.add(plan)
                    await session.flush()
                    session.add(
                        UserMembership(
                            user_id=owner.user_id,
                            plan_id=plan.id,
                            tier="PRESTIGE",
                            expires_at=starts,
                        )
                    )
                service = CommunityEventService(session)
                admin = _admin(owner)
                with pytest.raises(DomainError) as circle_config_error:
                    await service.create(
                        admin,
                        title="Circle không duyệt",
                        description="Không được tạo Circle thiếu điều kiện.",
                        starts_at=starts,
                        ends_at=starts + timedelta(hours=1),
                        location="Hà Nội",
                        required_tier="PRESTIGE",
                        capacity=5,
                        ticket_price_minor=0,
                        cancellation_cutoff_at=None,
                        included_entitlement="CIRCLE",
                        entitlement_quota=1,
                        requires_diamond_approval=False,
                    )
                assert circle_config_error.value.code == "INVALID_EVENT"
                event = await service.create(
                    admin,
                    title="Diamond Circle",
                    description="Dành riêng Kim cương.",
                    starts_at=starts,
                    ends_at=starts + timedelta(hours=1),
                    location="Hà Nội",
                    required_tier="PRESTIGE",
                    capacity=5,
                    ticket_price_minor=0,
                    cancellation_cutoff_at=None,
                    included_entitlement="CIRCLE",
                    entitlement_quota=1,
                    requires_diamond_approval=True,
                )
                await service.publish(admin, event.id)
                event_id = event.id
                with pytest.raises(DomainError) as pending_error:
                    await service.register(owner, event_id)
                assert pending_error.value.code == "DIAMOND_APPROVAL_REQUIRED"
                async with session.begin():
                    session.add(
                        MembershipDiamondApplication(
                            user_id=owner.user_id,
                            statement="Đơn đã được duyệt.",
                            status="APPROVED",
                        )
                    )
                    session.add(
                        MembershipEventEntitlementPolicy(
                            tier="PRESTIGE", entitlement="CIRCLE", quota_count=2
                        )
                    )
                registered = await service.register(owner, event_id)
                assert registered.status == "CONFIRMED"
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
