import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.advertising.errors import AdvertisingConflictError
from app.modules.advertising.inventory import (
    AdvertisingInventoryService,
    interval_capacity,
    peak_overlap,
)
from app.modules.advertising.models import (
    AdvertisingAuditLog,
    AdvertisingBooking,
    AdvertisingDiscountPolicy,
    AdvertisingOrder,
    AdvertisingPackage,
    AdvertisingPlacement,
    AdvertisingReservation,
)
from app.modules.advertising.schemas import AvailabilityData, QuoteData
from app.modules.auth.session_service import AuthPrincipal
from app.modules.wallet.models import Wallet, WalletJournal
from app.modules.wallet.service import WalletLedger
from app.tests.test_payment_service import ADMIN_ID, DOSSIER_ID, NOW, _service


def test_capacity_uses_full_half_open_interval_and_peak_overlap() -> None:
    start = datetime(2026, 11, 20, tzinfo=UTC)
    end = start + timedelta(days=30)
    staggered = [
        (start - timedelta(days=20), start + timedelta(days=10)),
        (start - timedelta(days=15), start + timedelta(days=15)),
        (start + timedelta(days=10), end + timedelta(days=10)),
        (start + timedelta(days=15), end + timedelta(days=15)),
    ]

    fits, remaining = interval_capacity(
        capacity=4, start_at=start, end_at=end, intervals=staggered
    )

    assert fits
    assert remaining == 2
    assert peak_overlap(staggered, now=start) == 2


def test_capacity_rejects_partial_overflow_but_allows_touching_boundaries() -> None:
    start = datetime(2026, 11, 20, tzinfo=UTC)
    end = start + timedelta(days=30)
    overlapping = [
        (start - timedelta(days=2), end - timedelta(days=1)),
        (start, start + timedelta(days=14)),
        (start + timedelta(days=10), end),
    ]
    fits, remaining = interval_capacity(
        capacity=3, start_at=start, end_at=end, intervals=overlapping
    )
    assert not fits
    assert remaining == 0

    adjacent_fits, remaining = interval_capacity(
        capacity=1,
        start_at=start,
        end_at=end,
        intervals=[(start - timedelta(hours=1), start)],
    )
    assert adjacent_fits
    assert remaining == 1


def test_booking_reservation_is_idempotent_and_expiry_releases_capacity() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner = await _service()
        current_time = [NOW]
        inventory = AdvertisingInventoryService(
            sessions(), clock=lambda: current_time[0]
        )
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=uuid4(),
            email="admin@cnsgroup.vn",
            roles=("SUPER_ADMIN",),
        )
        try:
            placement = AdvertisingPlacement(
                code="TEST_SLOT",
                name="Test slot",
                page_location="Test page",
                delivery_mode="EQUAL_ROTATION",
                capacity=1,
            )
            async with sessions() as session, session.begin():
                session.add(placement)
                await session.flush()
                package = AdvertisingPackage(
                    code="TEST_30D",
                    name="Test 30 days",
                    placement_id=placement.id,
                    duration_hours=720,
                    base_price_vnd=1_390_000,
                    price_version=1,
                    active=True,
                )
                session.add_all(
                    [
                        package,
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
                package_code="TEST_30D",
                title="First campaign",
                description="Test creative",
                image_url=None,
                destination_url="/cong-dong",
            )
            first_id = first.id
            await inventory.submit_campaign(owner, first_id)
            await inventory.review_campaign(admin, first_id, approve=True)

            second = await inventory.create_campaign(
                owner,
                dossier_id=DOSSIER_ID,
                package_code="TEST_30D",
                title="Second campaign",
                description="Test creative",
                image_url=None,
                destination_url="https://example.org/",
            )
            second_id = second.id
            await inventory.submit_campaign(owner, second_id)
            await inventory.review_campaign(admin, second_id, approve=True)

            begins = NOW + timedelta(days=5)
            reader = AdvertisingInventoryService(sessions(), clock=lambda: NOW)
            availability = await reader.availability(
                placement_code="TEST_SLOT",
                package_code="TEST_30D",
                start_at=begins,
            )
            assert AvailabilityData.model_validate(availability).available
            await reader.session.close()
            quote_reader = AdvertisingInventoryService(sessions(), clock=lambda: NOW)
            quote = await quote_reader.quote(owner, package_code="TEST_30D")
            assert QuoteData.model_validate(quote).payable_amount_vnd == 1_390_000
            await quote_reader.session.close()
            held = await inventory.reserve(
                owner,
                campaign_id=first_id,
                start_at=begins,
                idempotency_key="hold-first",
            )
            replay = await inventory.reserve(
                owner,
                campaign_id=first_id,
                start_at=begins,
                idempotency_key="hold-first",
            )
            assert replay.id == held.id

            with pytest.raises(AdvertisingConflictError) as conflict:
                await inventory.reserve(
                    owner,
                    campaign_id=second_id,
                    start_at=begins,
                    idempotency_key="hold-second",
                )
            assert conflict.value.code == "ADVERTISING_CAPACITY_FULL"
            assert len(conflict.value.details["availableDates"]) > 0

            waitlist_entry = await inventory.join_waitlist(
                owner, campaign_id=second_id, start_at=begins
            )
            await inventory.cancel_waitlist(owner, waitlist_entry.id)
            rejoined = await inventory.join_waitlist(
                owner, campaign_id=second_id, start_at=begins
            )
            assert rejoined.id == waitlist_entry.id
            assert rejoined.status == "WAITING"

            current_time[0] += timedelta(minutes=16)
            assert await inventory.expire_holds() == 1
            freed = await inventory.reserve(
                owner,
                campaign_id=second_id,
                start_at=begins,
                idempotency_key="hold-after-expiry",
            )
            assert freed.status == "HELD"

            async with sessions() as session:
                saved = await session.get(AdvertisingReservation, held.id)
                assert saved is not None and saved.status == "EXPIRED"
                expired_order = await session.scalar(
                    select(AdvertisingOrder).where(
                        AdvertisingOrder.reservation_id == held.id
                    )
                )
                assert expired_order is not None
                assert expired_order.payment_status == "EXPIRED"
                assert (
                    len(list(await session.scalars(select(AdvertisingAuditLog)))) >= 5
                )
        finally:
            await inventory.session.close()
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_wallet_checkout_confirms_booking_and_is_idempotent() -> None:
    async def exercise() -> None:
        payment_service, sessions, engine, owner = await _service()
        inventory = AdvertisingInventoryService(sessions())
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=uuid4(),
            email="admin@cnsgroup.vn",
            roles=("SUPER_ADMIN",),
        )
        try:
            placement = AdvertisingPlacement(
                code="PAYMENT_SLOT",
                name="Payment slot",
                page_location="Test page",
                delivery_mode="EQUAL_ROTATION",
                capacity=2,
            )
            async with sessions() as session, session.begin():
                session.add(placement)
                await session.flush()
                session.add_all(
                    [
                        AdvertisingPackage(
                            code="PAYMENT_30D",
                            name="Payment 30 days",
                            placement_id=placement.id,
                            duration_hours=720,
                            base_price_vnd=1_390_000,
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
                package_code="PAYMENT_30D",
                title="Wallet campaign",
                description="Approved creative",
                image_url=None,
                destination_url="/cong-dong",
            )
            campaign_id = campaign.id
            await inventory.submit_campaign(owner, campaign_id)
            await inventory.review_campaign(admin, campaign_id, approve=True)
            reservation = await inventory.reserve(
                owner,
                campaign_id=campaign_id,
                start_at=datetime.now(UTC) + timedelta(days=3),
                idempotency_key="wallet-reserve",
            )
            async with sessions() as session, session.begin():
                await WalletLedger(session).post(
                    user_id=owner.user_id,
                    delta=2_000_000,
                    kind="TOPUP",
                    key="advertising-test-funds",
                    reference="topup:advertising-test-funds",
                    description="Test wallet funds",
                )
                order = await session.scalar(
                    select(AdvertisingOrder).where(
                        AdvertisingOrder.reservation_id == reservation.id
                    )
                )
                assert order is not None
                order_id = order.id

            paid = await inventory.pay_order(
                owner, order_id, idempotency_key="advertising-payment"
            )
            replay = await inventory.pay_order(
                owner, order_id, idempotency_key="advertising-payment"
            )
            assert paid.payment_status == "PAID"
            assert replay.id == paid.id
            assert paid.wallet_transaction_id is not None
            async with sessions() as session:
                journal = await session.get(WalletJournal, paid.wallet_transaction_id)
                booking = await session.scalar(
                    select(AdvertisingBooking).where(
                        AdvertisingBooking.reservation_id == reservation.id
                    )
                )
                wallet = await session.get(Wallet, owner.user_id)
                assert journal is not None and journal.wallet_delta == -1_390_000
                assert booking is not None and booking.status == "CONFIRMED"
                assert wallet is not None and wallet.balance_minor == 610_000
        finally:
            await inventory.session.close()
            await payment_service.close()
            await engine.dispose()

    asyncio.run(exercise())
