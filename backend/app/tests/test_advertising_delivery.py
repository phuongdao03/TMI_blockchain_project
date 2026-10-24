import asyncio
from datetime import UTC, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.modules.advertising.admin import AdvertisingAdminService
from app.modules.advertising.delivery import (
    AdvertisingDeliveryService,
    is_valid_ad_traffic,
    select_weighted_round_robin,
)
from app.modules.advertising.inventory import AdvertisingInventoryService
from app.modules.advertising.models import (
    AdvertisingDiscountPolicy,
    AdvertisingOrder,
    AdvertisingPackage,
    AdvertisingPlacement,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVisibility
from app.modules.notifications.models import Notification
from app.modules.wallet.service import WalletLedger
from app.tests.test_payment_service import ADMIN_ID, DOSSIER_ID, NOW, _service


def test_equal_rotation_shares_selections_evenly() -> None:
    first = UUID("00000000-0000-4000-8000-000000000001")
    second = UUID("00000000-0000-4000-8000-000000000002")
    counts = {first: 0, second: 0}
    weights = {first: 1, second: 1}

    for _ in range(100):
        selected = select_weighted_round_robin(counts, weights)
        counts[selected] += 1

    assert counts == {first: 50, second: 50}


def test_weighted_rotation_converges_to_configured_ratio() -> None:
    first = UUID("00000000-0000-4000-8000-000000000001")
    second = UUID("00000000-0000-4000-8000-000000000002")
    counts = {first: 0, second: 0}
    weights = {first: 2, second: 1}

    for _ in range(90):
        selected = select_weighted_round_robin(counts, weights)
        counts[selected] += 1

    assert counts == {first: 60, second: 30}


def test_rotation_rejects_missing_or_invalid_weights() -> None:
    campaign_id = UUID("00000000-0000-4000-8000-000000000001")

    with pytest.raises(ValueError):
        select_weighted_round_robin({campaign_id: 0}, {})
    with pytest.raises(ValueError):
        select_weighted_round_robin({campaign_id: -1}, {campaign_id: 0})


def test_ad_traffic_excludes_automated_user_agents() -> None:
    assert is_valid_ad_traffic("Mozilla/5.0 (Windows NT 10.0) Chrome/130")
    assert not is_valid_ad_traffic("Googlebot/2.1 (+http://www.google.com/bot.html)")
    assert not is_valid_ad_traffic("")


def test_paid_campaign_starts_serves_and_records_deduplicated_metrics() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner = await _service()
        now = [NOW]
        inventory = AdvertisingInventoryService(sessions(), clock=lambda: now[0])
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=uuid4(),
            email="admin@example.test",
            roles=("SUPER_ADMIN",),
        )
        try:
            placement = AdvertisingPlacement(
                code="DELIVERY_TEST",
                name="Delivery test",
                page_location="Test",
                delivery_mode="EQUAL_ROTATION",
                capacity=1,
            )
            async with sessions() as session, session.begin():
                session.add(placement)
                await session.flush()
                session.add_all(
                    [
                        AdvertisingPackage(
                            code="DELIVERY_2H",
                            name="Two hours",
                            placement_id=placement.id,
                            duration_hours=2,
                            base_price_vnd=1_000,
                            price_version=1,
                            active=True,
                        ),
                        AdvertisingDiscountPolicy(
                            tier="MEMBER",
                            rate_basis_points=0,
                            annual_allowance_vnd=0,
                            policy_version=1,
                            active=True,
                        ),
                    ]
                )
                dossier = await session.get(Dossier, DOSSIER_ID)
                assert dossier is not None
                dossier._set_status_from_workflow(DossierStatus.PUBLISHED)
                dossier.visibility = DossierVisibility.PUBLIC
                dossier.published_at = NOW

            campaign = await inventory.create_campaign(
                owner,
                dossier_id=DOSSIER_ID,
                package_code="DELIVERY_2H",
                title="Public campaign",
                description="Eligible creative",
                image_url=None,
                destination_url="/cong-dong",
            )
            await inventory.submit_campaign(owner, campaign.id)
            await inventory.review_campaign(admin, campaign.id, approve=True)
            reservation = await inventory.reserve(
                owner,
                campaign_id=campaign.id,
                start_at=NOW + timedelta(minutes=1),
                idempotency_key="delivery-test-reservation",
            )
            async with sessions() as session, session.begin():
                await WalletLedger(session).post(
                    user_id=owner.user_id,
                    delta=2_000,
                    kind="TOPUP",
                    key="delivery-test-topup",
                    reference="topup:delivery-test-topup",
                    description="Test funds",
                )
                order = await session.scalar(
                    select(AdvertisingOrder).where(
                        AdvertisingOrder.reservation_id == reservation.id
                    )
                )
                assert order is not None
                order_id = order.id
            await inventory.pay_order(
                owner, order_id, idempotency_key="delivery-test-payment"
            )
            await inventory.update_package(
                admin,
                campaign.package_id,
                name=None,
                duration_hours=10,
                rotation_weight=None,
                base_price_vnd=None,
                terms=None,
                active=None,
            )

            now[0] = NOW + timedelta(minutes=2)
            lifecycle = AdvertisingDeliveryService(sessions(), clock=lambda: now[0])
            try:
                assert await lifecycle.advance_lifecycle() == 1
            finally:
                await lifecycle.session.close()
            async with sessions() as session:
                started = await session.get(type(campaign), campaign.id)
                assert started is not None
                assert started.actual_end_at is not None
                assert started.actual_end_at.replace(tzinfo=UTC) == NOW + timedelta(
                    minutes=2, hours=2
                )

            delivery = AdvertisingDeliveryService(sessions(), clock=lambda: now[0])
            try:
                ad = await delivery.select_ad(
                    "DELIVERY_TEST", user_agent="Mozilla/5.0 Chrome/130"
                )
                assert ad is not None
                assert ad["title"] == "Public campaign"
                assert await delivery.record_impression(
                    ad["event_id"], user_agent="Mozilla/5.0 Chrome/130"
                )
                assert not await delivery.record_impression(
                    ad["event_id"], user_agent="Mozilla/5.0 Chrome/130"
                )
                assert (
                    await delivery.record_click(
                        ad["event_id"], user_agent="Mozilla/5.0 Chrome/130"
                    )
                    == "/cong-dong"
                )
                assert (
                    await delivery.record_click(
                        ad["event_id"], user_agent="Mozilla/5.0 Chrome/130"
                    )
                    == "/cong-dong"
                )
                metrics = await delivery.campaign_metrics(owner, campaign.id)
                assert metrics["delivery_count"] == 1
                assert metrics["valid_impressions"] == 1
                assert metrics["valid_clicks"] == 1
                assert metrics["ctr_basis_points"] == 10_000
            finally:
                await delivery.session.close()
        finally:
            await inventory.session.close()
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_waitlist_notifies_owner_after_temporary_hold_expires() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner = await _service()
        now = [NOW]
        inventory = AdvertisingInventoryService(sessions(), clock=lambda: now[0])
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=uuid4(),
            email="admin@example.test",
            roles=("SUPER_ADMIN",),
        )
        try:
            placement = AdvertisingPlacement(
                code="WAITLIST_TEST",
                name="Waitlist test",
                page_location="Test",
                delivery_mode="EQUAL_ROTATION",
                capacity=1,
            )
            async with sessions() as session, session.begin():
                session.add(placement)
                await session.flush()
                session.add_all(
                    [
                        AdvertisingPackage(
                            code="WAITLIST_1H",
                            name="One hour",
                            placement_id=placement.id,
                            duration_hours=1,
                            base_price_vnd=1_000,
                            price_version=1,
                            active=True,
                        ),
                        AdvertisingDiscountPolicy(
                            tier="MEMBER",
                            rate_basis_points=0,
                            annual_allowance_vnd=0,
                            policy_version=1,
                            active=True,
                        ),
                    ]
                )

            first = await inventory.create_campaign(
                owner,
                dossier_id=DOSSIER_ID,
                package_code="WAITLIST_1H",
                title="First",
                description="First creative",
                image_url=None,
                destination_url="/",
            )
            second = await inventory.create_campaign(
                owner,
                dossier_id=DOSSIER_ID,
                package_code="WAITLIST_1H",
                title="Second",
                description="Second creative",
                image_url=None,
                destination_url="/",
            )
            for campaign in (first, second):
                await inventory.submit_campaign(owner, campaign.id)
                await inventory.review_campaign(admin, campaign.id, approve=True)
            start = NOW + timedelta(days=3)
            await inventory.reserve(
                owner,
                campaign_id=first.id,
                start_at=start,
                idempotency_key="waitlist-blocking-hold",
            )
            entry = await inventory.join_waitlist(
                owner, campaign_id=second.id, start_at=start
            )
            replay = await inventory.join_waitlist(
                owner, campaign_id=second.id, start_at=start
            )
            assert replay.id == entry.id
            assert entry.status == "WAITING"

            now[0] += timedelta(minutes=16)
            notifier = AdvertisingInventoryService(sessions(), clock=lambda: now[0])
            try:
                assert await notifier.notify_available_waitlists() == 1
            finally:
                await notifier.session.close()
            async with sessions() as session:
                saved = await session.get(type(entry), entry.id)
                notice = await session.scalar(select(Notification))
                assert saved is not None and saved.status == "NOTIFIED"
                assert notice is not None
                assert notice.user_id == owner.user_id
                assert notice.type == "ADVERTISING_WAITLIST_AVAILABLE"
        finally:
            await inventory.session.close()
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_admin_inventory_shows_holds_and_report_aggregates() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner = await _service()
        inventory = AdvertisingInventoryService(sessions(), clock=lambda: NOW)
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=uuid4(),
            email="admin@example.test",
            roles=("SUPER_ADMIN",),
        )
        try:
            placement = AdvertisingPlacement(
                code="ADMIN_INVENTORY_TEST",
                name="Admin inventory test",
                page_location="Test",
                delivery_mode="EQUAL_ROTATION",
                capacity=1,
            )
            async with sessions() as session, session.begin():
                session.add(placement)
                await session.flush()
                session.add_all(
                    [
                        AdvertisingPackage(
                            code="ADMIN_INVENTORY_1H",
                            name="One hour",
                            placement_id=placement.id,
                            duration_hours=1,
                            base_price_vnd=1_000,
                            price_version=1,
                            active=True,
                        ),
                        AdvertisingDiscountPolicy(
                            tier="MEMBER",
                            rate_basis_points=0,
                            annual_allowance_vnd=0,
                            policy_version=1,
                            active=True,
                        ),
                    ]
                )
            campaign = await inventory.create_campaign(
                owner,
                dossier_id=DOSSIER_ID,
                package_code="ADMIN_INVENTORY_1H",
                title="Admin inventory campaign",
                description="Creative",
                image_url=None,
                destination_url="/",
            )
            await inventory.submit_campaign(owner, campaign.id)
            await inventory.review_campaign(admin, campaign.id, approve=True)
            await inventory.reserve(
                owner,
                campaign_id=campaign.id,
                start_at=NOW + timedelta(days=1),
                idempotency_key="admin-inventory-hold",
            )
            reports = AdvertisingAdminService(sessions())
            try:
                slots = await reports.inventory(
                    admin,
                    start_at=NOW,
                    end_at=NOW + timedelta(days=3),
                )
                report = await reports.reports(
                    admin,
                    start_date=NOW.date(),
                    end_date=(NOW + timedelta(days=3)).date(),
                )
                selected_slot = next(
                    slot for slot in slots if slot["code"] == placement.code
                )
                selected_report = next(
                    row for row in report if row["placement_code"] == placement.code
                )
                assert len(selected_slot["reservations"]) == 1
                assert selected_slot["bookings"] == []
                assert selected_report["paid_orders"] == 0
                assert selected_report["campaigns"] == []
            finally:
                await reports.session.close()
        finally:
            await inventory.session.close()
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_admin_can_configure_inventory_and_owner_can_list_campaigns() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner = await _service()
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=uuid4(),
            email="admin@example.test",
            roles=("SUPER_ADMIN",),
        )
        try:
            inventory = AdvertisingInventoryService(sessions(), clock=lambda: NOW)
            try:
                placement = await inventory.create_placement(
                    admin,
                    code="NEW_AD_SLOT",
                    name="New placement",
                    page_location="Home page",
                    delivery_mode="WEIGHTED_ROTATION",
                    capacity=3,
                    timezone="Asia/Bangkok",
                )
                package = await inventory.create_package(
                    admin,
                    code="NEW_AD_PACKAGE",
                    name="New package",
                    placement_id=placement.id,
                    duration_hours=24,
                    rotation_weight=3,
                    base_price_vnd=250_000,
                    active=True,
                    terms="Time based placement.",
                )
                campaign = await inventory.create_campaign(
                    owner,
                    dossier_id=DOSSIER_ID,
                    package_code=package.code,
                    title="Configured campaign",
                    description="Campaign summary test",
                    image_url=None,
                    destination_url="/",
                )
                rows = await inventory.list_campaigns(owner)
                summary = next(row for row in rows if row["id"] == campaign.id)
                assert package.rotation_weight == 3
                assert campaign.rotation_weight == 3
                assert summary["creative_title"] == "Configured campaign"
                assert summary["creative_description"] == "Campaign summary test"
                assert summary["destination_url"] == "/"
                assert summary["placement_code"] == "NEW_AD_SLOT"
                assert summary["payment_status"] is None
            finally:
                await inventory.session.close()
        finally:
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_moderation_changes_create_a_new_reviewable_creative_version() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner = await _service()
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=uuid4(),
            email="admin@example.test",
            roles=("SUPER_ADMIN",),
        )
        inventory = AdvertisingInventoryService(sessions(), clock=lambda: NOW)
        try:
            placement = AdvertisingPlacement(
                code="MODERATION_TEST",
                name="Moderation test",
                page_location="Test",
                delivery_mode="EQUAL_ROTATION",
                capacity=1,
            )
            async with sessions() as session, session.begin():
                session.add(placement)
                await session.flush()
                session.add_all(
                    [
                        AdvertisingPackage(
                            code="MODERATION_1D",
                            name="One day",
                            placement_id=placement.id,
                            duration_hours=24,
                            base_price_vnd=1_000,
                            price_version=1,
                            active=True,
                        ),
                        AdvertisingDiscountPolicy(
                            tier="MEMBER",
                            rate_basis_points=0,
                            annual_allowance_vnd=0,
                            policy_version=1,
                            active=True,
                        ),
                    ]
                )
            campaign = await inventory.create_campaign(
                owner,
                dossier_id=DOSSIER_ID,
                package_code="MODERATION_1D",
                title="Original creative",
                description="Needs revision",
                image_url=None,
                destination_url="/",
            )
            await inventory.submit_campaign(owner, campaign.id)
            await inventory.review_campaign(
                admin,
                campaign.id,
                decision="CHANGES_REQUESTED",
                reason="Use a clearer description.",
            )
            summary = next(
                row
                for row in await inventory.list_campaigns(owner)
                if row["id"] == campaign.id
            )
            assert summary["creative_review_status"] == "CHANGES_REQUESTED"
            assert summary["creative_review_note"] == "Use a clearer description."
            await inventory.session.close()

            workflow = AdvertisingInventoryService(sessions(), clock=lambda: NOW)
            revised = await workflow.update_campaign_creative(
                owner,
                campaign.id,
                title="Revised creative",
                description="Updated description",
                image_url=None,
                destination_url="/revised",
            )
            await workflow.submit_campaign(owner, campaign.id)
            queue = AdvertisingAdminService(sessions())
            try:
                review_items = await queue.campaign_review_queue(admin)
                item = next(
                    row for row in review_items if row["campaign_id"] == campaign.id
                )
                assert item["creative_version"] == 2
                assert item["creative_id"] == revised.id
                assert item["destination_url"] == "/revised"
            finally:
                await queue.session.close()
            approved = await workflow.review_campaign(
                admin, campaign.id, decision="APPROVE"
            )
            assert approved.status == "APPROVED"
            await workflow.session.close()
        finally:
            await inventory.session.close()
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())
