import re
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime, timedelta
from typing import TypedDict
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.advertising.errors import (
    AdvertisingConflictError,
    AdvertisingForbiddenError,
    AdvertisingNotFoundError,
)
from app.modules.advertising.models import (
    AdvertisingAuditLog,
    AdvertisingBooking,
    AdvertisingCampaign,
    AdvertisingCreative,
    AdvertisingDiscountPolicy,
    AdvertisingOrder,
    AdvertisingPackage,
    AdvertisingPlacement,
    AdvertisingReservation,
    AdvertisingWaitlistEntry,
)
from app.modules.auth.models import User
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVisibility
from app.modules.memberships.cycle import active_membership_cycle
from app.modules.notifications.service import NotificationService
from app.modules.wallet.models import WalletJournal
from app.modules.wallet.service import WalletLedger

Interval = tuple[datetime, datetime]
RESERVATION_TTL = timedelta(minutes=15)
ALTERNATIVE_SEARCH_DAYS = 30
MEMBERSHIP_DISCOUNT_ALLOWANCE = {
    "MEMBER": 0,
    "SILVER": 150_000,
    "COMPANION": 600_000,
    "PRESTIGE": 2_000_000,
}


class AvailabilityView(TypedDict):
    placement: AdvertisingPlacement
    package: AdvertisingPackage
    start_at: datetime
    end_at: datetime
    available: bool
    remaining_slots: int
    alternatives: list[datetime]


class QuoteView(TypedDict):
    placement_code: str
    placement_name: str
    package_code: str
    package_name: str
    duration_hours: int
    membership_tier: str
    membership_cycle_start: datetime | None
    discount_policy_version: int
    discount_rate_basis_points: int
    remaining_discount_allowance_vnd: int
    base_amount_vnd: int
    discount_amount_vnd: int
    payable_amount_vnd: int
    price_version: int


class CampaignSummaryView(TypedDict):
    id: UUID
    dossier_id: UUID
    package_id: UUID
    placement_id: UUID
    placement_code: str
    placement_name: str
    purchase_context: str
    status: str
    desired_start_at: datetime | None
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    booking_start_at: datetime | None
    booking_end_at: datetime | None
    creative_title: str | None
    creative_description: str | None
    image_url: str | None
    destination_url: str | None
    creative_review_status: str | None
    creative_review_note: str | None
    payment_status: str | None
    delivery_count: int
    created_at: datetime


class WaitlistView(TypedDict):
    id: UUID
    campaign_id: UUID
    placement_id: UUID
    start_at: datetime
    end_at: datetime
    status: str
    created_at: datetime


class RenewalQuoteView(TypedDict):
    quote: QuoteView
    availability: AvailabilityView


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise DomainError(
            code="ADVERTISING_INVALID_TIMESTAMP",
            message="Thời gian quảng cáo phải có múi giờ.",
            status_code=422,
        )
    return value.astimezone(UTC)


def _db_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def interval_capacity(
    *,
    capacity: int,
    start_at: datetime,
    end_at: datetime,
    intervals: Iterable[Interval],
) -> tuple[bool, int]:
    """Return fit and minimum remaining slots across a half-open UTC interval."""
    start, end = _utc(start_at), _utc(end_at)
    if start >= end or capacity < 1:
        raise ValueError("A valid interval and positive capacity are required.")

    events: dict[datetime, int] = {}
    for existing_start, existing_end in intervals:
        occupied_start = max(start, _db_utc(existing_start))
        occupied_end = min(end, _db_utc(existing_end))
        if occupied_start < occupied_end:
            events[occupied_start] = events.get(occupied_start, 0) + 1
            events[occupied_end] = events.get(occupied_end, 0) - 1

    occupied = 0
    remaining = capacity
    for event_at in sorted(events):
        occupied += events[event_at]
        remaining = min(remaining, capacity - occupied)
    return remaining > 0, remaining


def peak_overlap(intervals: Iterable[Interval], *, now: datetime) -> int:
    """Return maximum simultaneous occupancy for active half-open intervals."""
    events: dict[datetime, int] = {}
    current_time = _utc(now)
    for start_at, end_at in intervals:
        start, end = _db_utc(start_at), _db_utc(end_at)
        if start < current_time:
            start = current_time
        if start < end:
            events[start] = events.get(start, 0) + 1
            events[end] = events.get(end, 0) - 1
    occupancy = peak = 0
    for event_at in sorted(events):
        occupancy += events[event_at]
        peak = max(peak, occupancy)
    return peak


class AdvertisingInventoryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Callable[[], datetime] | None = None,
        reservation_ttl: timedelta = RESERVATION_TTL,
    ) -> None:
        self.session = session
        self.clock = clock or (lambda: datetime.now(UTC))
        self.reservation_ttl = reservation_ttl

    async def list_placements(self) -> list[AdvertisingPlacement]:
        return list(
            await self.session.scalars(
                select(AdvertisingPlacement)
                .where(AdvertisingPlacement.enabled.is_(True))
                .order_by(AdvertisingPlacement.name)
            )
        )

    async def list_campaigns(
        self, principal: AuthPrincipal
    ) -> list[CampaignSummaryView]:
        latest_version = (
            select(func.max(AdvertisingCreative.version))
            .where(AdvertisingCreative.campaign_id == AdvertisingCampaign.id)
            .correlate(AdvertisingCampaign)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(
                    AdvertisingCampaign,
                    AdvertisingPlacement,
                    AdvertisingBooking,
                    AdvertisingOrder,
                    AdvertisingCreative,
                )
                .join(
                    AdvertisingPlacement,
                    AdvertisingPlacement.id == AdvertisingCampaign.placement_id,
                )
                .outerjoin(
                    AdvertisingBooking,
                    AdvertisingBooking.campaign_id == AdvertisingCampaign.id,
                )
                .outerjoin(
                    AdvertisingOrder,
                    AdvertisingOrder.reservation_id
                    == AdvertisingBooking.reservation_id,
                )
                .outerjoin(
                    AdvertisingCreative,
                    and_(
                        AdvertisingCreative.campaign_id == AdvertisingCampaign.id,
                        AdvertisingCreative.version == latest_version,
                    ),
                )
                .where(AdvertisingCampaign.owner_user_id == principal.user_id)
                .order_by(AdvertisingCampaign.created_at.desc())
            )
        ).all()
        return [
            {
                "id": campaign.id,
                "dossier_id": campaign.dossier_id,
                "package_id": campaign.package_id,
                "placement_id": placement.id,
                "placement_code": placement.code,
                "placement_name": placement.name,
                "purchase_context": campaign.purchase_context,
                "status": campaign.status,
                "desired_start_at": campaign.desired_start_at,
                "actual_start_at": campaign.actual_start_at,
                "actual_end_at": campaign.actual_end_at,
                "booking_start_at": booking.start_at if booking else None,
                "booking_end_at": booking.end_at if booking else None,
                "creative_title": creative.title if creative else None,
                "creative_description": creative.description if creative else None,
                "image_url": creative.image_url if creative else None,
                "destination_url": creative.destination_url if creative else None,
                "creative_review_status": creative.review_status if creative else None,
                "creative_review_note": creative.review_note if creative else None,
                "payment_status": order.payment_status if order else None,
                "delivery_count": campaign.delivery_count,
                "created_at": campaign.created_at,
            }
            for campaign, placement, booking, order, creative in rows
        ]

    async def create_placement(
        self,
        principal: AuthPrincipal,
        *,
        code: str,
        name: str,
        page_location: str,
        delivery_mode: str,
        capacity: int,
        timezone: str,
    ) -> AdvertisingPlacement:
        self._require_admin(principal)
        normalized_code = code.strip().upper()
        if (
            not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", normalized_code)
            or not name.strip()
            or not page_location.strip()
        ):
            raise AdvertisingConflictError("Placement fields cannot be empty.")
        normalized_timezone = timezone.strip() or "Asia/Bangkok"
        try:
            ZoneInfo(normalized_timezone)
        except ZoneInfoNotFoundError as error:
            raise AdvertisingConflictError("Unknown placement timezone.") from error
        if delivery_mode not in {
            "EQUAL_ROTATION",
            "WEIGHTED_ROTATION",
            "EXCLUSIVE",
        }:
            raise AdvertisingConflictError("Invalid delivery mode.")
        if delivery_mode == "EXCLUSIVE":
            if capacity != 1:
                raise AdvertisingConflictError(
                    "Exclusive placements must have capacity one."
                )
        elif not 1 <= capacity <= 100:
            raise AdvertisingConflictError("Capacity must be between 1 and 100.")
        async with self.session.begin():
            exists = await self.session.scalar(
                select(AdvertisingPlacement.id).where(
                    AdvertisingPlacement.code == normalized_code
                )
            )
            if exists is not None:
                raise AdvertisingConflictError("Placement code already exists.")
            placement = AdvertisingPlacement(
                code=normalized_code,
                name=name.strip(),
                page_location=page_location.strip(),
                delivery_mode=delivery_mode,
                capacity=capacity,
                timezone=normalized_timezone,
            )
            self.session.add(placement)
            await self.session.flush()
            self._audit(
                actor_id=principal.user_id,
                entity_type="placement",
                entity_id=placement.id,
                action="placement.created",
                after={
                    "code": placement.code,
                    "name": placement.name,
                    "capacity": placement.capacity,
                    "delivery_mode": placement.delivery_mode,
                },
            )
            await self.session.flush()
            return placement

    async def create_package(
        self,
        principal: AuthPrincipal,
        *,
        code: str,
        name: str,
        placement_id: UUID,
        duration_hours: int,
        rotation_weight: int,
        base_price_vnd: int,
        active: bool,
        terms: str,
    ) -> AdvertisingPackage:
        self._require_admin(principal)
        normalized_code = code.strip().upper()
        if (
            not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", normalized_code)
            or not name.strip()
        ):
            raise AdvertisingConflictError("Package code and name are required.")
        if not 1 <= duration_hours <= 8760 or not 1 <= rotation_weight <= 100:
            raise AdvertisingConflictError("Package duration or weight is invalid.")
        if base_price_vnd < 0:
            raise AdvertisingConflictError("Package price cannot be negative.")
        async with self.session.begin():
            placement = await self.session.scalar(
                select(AdvertisingPlacement)
                .where(AdvertisingPlacement.id == placement_id)
                .with_for_update()
            )
            if placement is None:
                raise AdvertisingNotFoundError()
            exists = await self.session.scalar(
                select(AdvertisingPackage.id).where(
                    AdvertisingPackage.code == normalized_code
                )
            )
            if exists is not None:
                raise AdvertisingConflictError("Package code already exists.")
            package = AdvertisingPackage(
                code=normalized_code,
                name=name.strip(),
                placement_id=placement.id,
                duration_hours=duration_hours,
                rotation_weight=rotation_weight,
                base_price_vnd=base_price_vnd,
                price_version=1,
                active=active,
                terms=terms.strip(),
            )
            self.session.add(package)
            await self.session.flush()
            self._audit(
                actor_id=principal.user_id,
                entity_type="package",
                entity_id=package.id,
                action="package.created",
                after={
                    "code": package.code,
                    "placement_id": str(package.placement_id),
                    "base_price_vnd": package.base_price_vnd,
                    "duration_hours": package.duration_hours,
                },
            )
            await self.session.flush()
            return package

    async def quote(self, principal: AuthPrincipal, *, package_code: str) -> QuoteView:
        placement, package = await self._catalog_entry_by_package(package_code)
        return await self._quote_for_user(
            principal.user_id, placement=placement, package=package, lock_policy=False
        )

    async def renewal_quote(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        start_at: datetime,
    ) -> RenewalQuoteView:
        campaign = await self.session.scalar(
            select(AdvertisingCampaign).where(
                AdvertisingCampaign.id == campaign_id,
                AdvertisingCampaign.owner_user_id == principal.user_id,
            )
        )
        if campaign is None:
            raise AdvertisingNotFoundError()
        if campaign.status not in {"ACTIVE", "COMPLETED"}:
            raise AdvertisingConflictError(
                "Only active or completed campaigns can be renewed."
            )
        stored_package = await self.session.get(AdvertisingPackage, campaign.package_id)
        if stored_package is None:
            raise AdvertisingNotFoundError()
        placement, package = await self._catalog_entry_by_package(stored_package.code)
        availability = await self.availability(
            placement_code=placement.code,
            package_code=package.code,
            start_at=start_at,
        )
        quote = await self._quote_for_user(
            principal.user_id,
            placement=placement,
            package=package,
            lock_policy=False,
        )
        return {"quote": quote, "availability": availability}

    async def update_discount_policy(
        self,
        principal: AuthPrincipal,
        tier: str,
        *,
        rate_basis_points: int,
        annual_allowance_vnd: int,
        active: bool,
    ) -> AdvertisingDiscountPolicy:
        self._require_admin(principal)
        normalized_tier = tier.upper()
        if normalized_tier not in MEMBERSHIP_DISCOUNT_ALLOWANCE:
            raise AdvertisingNotFoundError()
        if not 0 <= rate_basis_points <= 10_000 or annual_allowance_vnd < 0:
            raise AdvertisingConflictError("Chính sách ưu đãi không hợp lệ.")
        async with self.session.begin():
            policy = await self.session.scalar(
                select(AdvertisingDiscountPolicy)
                .where(AdvertisingDiscountPolicy.tier == normalized_tier)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if policy is None:
                raise AdvertisingNotFoundError()
            before = {
                "rate_basis_points": policy.rate_basis_points,
                "annual_allowance_vnd": policy.annual_allowance_vnd,
                "active": policy.active,
                "policy_version": policy.policy_version,
            }
            changed = (
                policy.rate_basis_points != rate_basis_points
                or policy.annual_allowance_vnd != annual_allowance_vnd
                or policy.active != active
            )
            policy.rate_basis_points = rate_basis_points
            policy.annual_allowance_vnd = annual_allowance_vnd
            policy.active = active
            if changed:
                policy.policy_version += 1
            self._audit(
                actor_id=principal.user_id,
                entity_type="discount_policy",
                entity_id=policy.id,
                action="discount_policy.updated",
                before=before,
                after={
                    "tier": policy.tier,
                    "rate_basis_points": policy.rate_basis_points,
                    "annual_allowance_vnd": policy.annual_allowance_vnd,
                    "active": policy.active,
                    "policy_version": policy.policy_version,
                },
            )
            await self.session.flush()
            return policy

    async def list_packages(
        self, *, placement_code: str | None = None
    ) -> list[tuple[AdvertisingPackage, AdvertisingPlacement]]:
        query = (
            select(AdvertisingPackage, AdvertisingPlacement)
            .join(
                AdvertisingPlacement,
                AdvertisingPlacement.id == AdvertisingPackage.placement_id,
            )
            .where(
                AdvertisingPackage.active.is_(True),
                AdvertisingPlacement.enabled.is_(True),
            )
            .order_by(AdvertisingPlacement.name, AdvertisingPackage.name)
        )
        if placement_code is not None:
            query = query.where(AdvertisingPlacement.code == placement_code)
        rows = (await self.session.execute(query)).all()
        return [(package, placement) for package, placement in rows]

    async def update_placement(
        self,
        principal: AuthPrincipal,
        placement_id: UUID,
        *,
        name: str | None,
        page_location: str | None,
        delivery_mode: str | None,
        capacity: int | None,
        enabled: bool | None,
    ) -> AdvertisingPlacement:
        self._require_admin(principal)
        async with self.session.begin():
            placement = await self.session.scalar(
                select(AdvertisingPlacement)
                .where(AdvertisingPlacement.id == placement_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if placement is None:
                raise AdvertisingNotFoundError()
            before = {
                "name": placement.name,
                "page_location": placement.page_location,
                "delivery_mode": placement.delivery_mode,
                "capacity": placement.capacity,
                "enabled": placement.enabled,
            }
            next_capacity = capacity if capacity is not None else placement.capacity
            next_mode = delivery_mode or placement.delivery_mode
            if next_mode == "EXCLUSIVE":
                next_capacity = 1
                if capacity not in {None, 1}:
                    raise AdvertisingConflictError(
                        "Vị trí độc quyền phải có đúng một suất."
                    )
            if next_capacity < 1:
                raise AdvertisingConflictError("Số suất phải lớn hơn không.")
            active_intervals = await self._committed_intervals(
                placement.id, _utc(self.clock())
            )
            peak = peak_overlap(active_intervals, now=_utc(self.clock()))
            if next_capacity < peak:
                raise AdvertisingConflictError(
                    "Số suất mới thấp hơn số booking đang cam kết.",
                    details={"minimumCapacity": peak},
                )
            placement.name = name.strip() if name is not None else placement.name
            placement.page_location = (
                page_location.strip()
                if page_location is not None
                else placement.page_location
            )
            placement.delivery_mode = next_mode
            placement.capacity = next_capacity
            if enabled is not None:
                placement.enabled = enabled
            after = {
                "name": placement.name,
                "page_location": placement.page_location,
                "delivery_mode": placement.delivery_mode,
                "capacity": placement.capacity,
                "enabled": placement.enabled,
            }
            self._audit(
                actor_id=principal.user_id,
                entity_type="placement",
                entity_id=placement.id,
                action="placement.updated",
                before=before,
                after=after,
            )
            await self.session.flush()
            return placement

    async def pause_campaign(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        reason: str,
    ) -> AdvertisingCampaign:
        self._require_admin(principal)
        async with self.session.begin():
            campaign_ref = await self.session.scalar(
                select(AdvertisingCampaign).where(AdvertisingCampaign.id == campaign_id)
            )
            if campaign_ref is None:
                raise AdvertisingNotFoundError()
            await self.session.scalar(
                select(AdvertisingPlacement.id)
                .where(AdvertisingPlacement.id == campaign_ref.placement_id)
                .with_for_update()
            )
            campaign = await self._campaign(campaign_id, for_update=True)
            if campaign.status == "PAUSED":
                return campaign
            if campaign.status not in {"SCHEDULED", "ACTIVE"}:
                raise AdvertisingConflictError(
                    "Only a scheduled or active campaign can be paused."
                )
            before = {"status": campaign.status}
            campaign.status = "PAUSED"
            self._audit(
                actor_id=principal.user_id,
                entity_type="campaign",
                entity_id=campaign.id,
                action="campaign.paused",
                before=before,
                after={"status": campaign.status, "reason": reason.strip()},
            )
            await self.session.flush()
            return campaign

    async def update_package(
        self,
        principal: AuthPrincipal,
        package_id: UUID,
        *,
        name: str | None,
        duration_hours: int | None,
        rotation_weight: int | None,
        base_price_vnd: int | None,
        terms: str | None,
        active: bool | None,
    ) -> AdvertisingPackage:
        self._require_admin(principal)
        async with self.session.begin():
            package = await self.session.scalar(
                select(AdvertisingPackage)
                .where(AdvertisingPackage.id == package_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if package is None:
                raise AdvertisingNotFoundError()
            before = {
                "name": package.name,
                "duration_hours": package.duration_hours,
                "rotation_weight": package.rotation_weight,
                "base_price_vnd": package.base_price_vnd,
                "price_version": package.price_version,
                "active": package.active,
            }
            changed = any(
                value is not None and value != getattr(package, field)
                for field, value in (
                    ("name", name.strip() if name is not None else None),
                    ("duration_hours", duration_hours),
                    ("rotation_weight", rotation_weight),
                    ("base_price_vnd", base_price_vnd),
                    ("terms", terms),
                )
            )
            if duration_hours is not None and duration_hours < 1:
                raise AdvertisingConflictError("Thời hạn gói phải lớn hơn không.")
            if rotation_weight is not None and not 1 <= rotation_weight <= 100:
                raise AdvertisingConflictError("Invalid rotation weight.")
            if base_price_vnd is not None and base_price_vnd < 0:
                raise AdvertisingConflictError("Giá gói không hợp lệ.")
            if name is not None:
                package.name = name.strip()
            if duration_hours is not None:
                package.duration_hours = duration_hours
            if rotation_weight is not None:
                package.rotation_weight = rotation_weight
            if base_price_vnd is not None:
                package.base_price_vnd = base_price_vnd
            if terms is not None:
                package.terms = terms.strip()
            if active is not None:
                package.active = active
            if changed:
                package.price_version += 1
            self._audit(
                actor_id=principal.user_id,
                entity_type="package",
                entity_id=package.id,
                action="package.updated",
                before=before,
                after={
                    "name": package.name,
                    "duration_hours": package.duration_hours,
                    "rotation_weight": package.rotation_weight,
                    "base_price_vnd": package.base_price_vnd,
                    "price_version": package.price_version,
                    "active": package.active,
                },
            )
            await self.session.flush()
            return package

    async def join_waitlist(
        self,
        principal: AuthPrincipal,
        *,
        campaign_id: UUID,
        start_at: datetime,
    ) -> AdvertisingWaitlistEntry:
        start = _utc(start_at)
        now = _utc(self.clock())
        if start < now:
            raise AdvertisingConflictError("Waitlist date must be in the future.")
        async with self.session.begin():
            campaign_ref = await self.session.scalar(
                select(AdvertisingCampaign).where(AdvertisingCampaign.id == campaign_id)
            )
            if campaign_ref is None:
                raise AdvertisingNotFoundError()
            if campaign_ref.owner_user_id != principal.user_id:
                raise AdvertisingForbiddenError()
            placement = await self.session.scalar(
                select(AdvertisingPlacement)
                .where(AdvertisingPlacement.id == campaign_ref.placement_id)
                .with_for_update()
            )
            campaign = await self._campaign(campaign_id, for_update=True)
            if placement is None:
                raise AdvertisingNotFoundError()
            if campaign.status != "APPROVED":
                raise AdvertisingConflictError(
                    "Campaign must be approved before joining a waitlist."
                )
            existing = await self.session.scalar(
                select(AdvertisingWaitlistEntry)
                .where(
                    AdvertisingWaitlistEntry.owner_user_id == principal.user_id,
                    AdvertisingWaitlistEntry.campaign_id == campaign.id,
                    AdvertisingWaitlistEntry.start_at == start,
                )
                .with_for_update()
            )
            if existing is not None and existing.status in {"WAITING", "NOTIFIED"}:
                return existing
            if existing is not None and existing.status != "CANCELLED":
                raise AdvertisingConflictError(
                    "This waitlist entry has already been fulfilled."
                )
            package = await self.session.scalar(
                select(AdvertisingPackage).where(
                    AdvertisingPackage.id == campaign.package_id
                )
            )
            if package is None:
                raise AdvertisingNotFoundError()
            end = start + timedelta(hours=package.duration_hours)
            await self._expire_holds(placement.id, now)
            intervals = await self._active_intervals(placement.id, start, end)
            fits, _ = interval_capacity(
                capacity=placement.capacity,
                start_at=start,
                end_at=end,
                intervals=intervals,
            )
            if fits:
                raise AdvertisingConflictError(
                    "Capacity is available for the requested schedule.",
                    code="ADVERTISING_CAPACITY_AVAILABLE",
                )
            if existing is not None:
                existing.end_at = end
                existing.status = "WAITING"
                self._audit(
                    actor_id=principal.user_id,
                    entity_type="waitlist",
                    entity_id=existing.id,
                    action="waitlist.rejoined",
                    after={"status": existing.status, "end_at": end.isoformat()},
                )
                await self.session.flush()
                return existing
            entry = AdvertisingWaitlistEntry(
                owner_user_id=principal.user_id,
                campaign_id=campaign.id,
                placement_id=placement.id,
                start_at=start,
                end_at=end,
                status="WAITING",
            )
            self.session.add(entry)
            await self.session.flush()
            self._audit(
                actor_id=principal.user_id,
                entity_type="waitlist",
                entity_id=entry.id,
                action="waitlist.joined",
                after={
                    "campaign_id": str(campaign.id),
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat(),
                },
            )
            await self.session.flush()
            return entry

    async def list_waitlist(
        self, principal: AuthPrincipal
    ) -> list[AdvertisingWaitlistEntry]:
        return list(
            await self.session.scalars(
                select(AdvertisingWaitlistEntry)
                .where(AdvertisingWaitlistEntry.owner_user_id == principal.user_id)
                .order_by(AdvertisingWaitlistEntry.created_at.desc())
            )
        )

    async def cancel_waitlist(
        self, principal: AuthPrincipal, entry_id: UUID
    ) -> AdvertisingWaitlistEntry:
        async with self.session.begin():
            entry = await self.session.scalar(
                select(AdvertisingWaitlistEntry)
                .where(
                    AdvertisingWaitlistEntry.id == entry_id,
                    AdvertisingWaitlistEntry.owner_user_id == principal.user_id,
                )
                .with_for_update()
            )
            if entry is None:
                raise AdvertisingNotFoundError()
            if entry.status not in {"WAITING", "NOTIFIED"}:
                raise AdvertisingConflictError("Waitlist entry cannot be cancelled.")
            entry.status = "CANCELLED"
            self._audit(
                actor_id=principal.user_id,
                entity_type="waitlist",
                entity_id=entry.id,
                action="waitlist.cancelled",
                after={"status": entry.status},
            )
            await self.session.flush()
            return entry

    async def notify_available_waitlists(self, *, limit: int = 500) -> int:
        now = _utc(self.clock())
        async with self.session.begin():
            placement_ids = list(
                await self.session.scalars(
                    select(AdvertisingWaitlistEntry.placement_id)
                    .where(AdvertisingWaitlistEntry.status == "WAITING")
                    .distinct()
                    .order_by(AdvertisingWaitlistEntry.placement_id)
                    .limit(limit)
                )
            )
        notified = 0
        for placement_id in placement_ids:
            async with self.session.begin():
                placement = await self.session.scalar(
                    select(AdvertisingPlacement)
                    .where(AdvertisingPlacement.id == placement_id)
                    .with_for_update()
                )
                if placement is None:
                    continue
                entries = list(
                    await self.session.scalars(
                        select(AdvertisingWaitlistEntry)
                        .where(
                            AdvertisingWaitlistEntry.placement_id == placement.id,
                            AdvertisingWaitlistEntry.status == "WAITING",
                        )
                        .order_by(
                            AdvertisingWaitlistEntry.created_at,
                            AdvertisingWaitlistEntry.id,
                        )
                        .with_for_update()
                    )
                )
                for entry in entries:
                    if _db_utc(entry.start_at) <= now or _db_utc(entry.end_at) <= now:
                        entry.status = "CANCELLED"
                        self._audit(
                            actor_id=None,
                            entity_type="waitlist",
                            entity_id=entry.id,
                            action="waitlist.expired",
                            after={"status": entry.status},
                        )
                        continue
                    intervals = await self._active_intervals(
                        placement.id, _db_utc(entry.start_at), _db_utc(entry.end_at)
                    )
                    fits, _ = interval_capacity(
                        capacity=placement.capacity,
                        start_at=_db_utc(entry.start_at),
                        end_at=_db_utc(entry.end_at),
                        intervals=intervals,
                    )
                    if not fits:
                        continue
                    entry.status = "NOTIFIED"
                    await NotificationService(self.session).consume_in_transaction(
                        event_id=entry.id,
                        user_id=entry.owner_user_id,
                        event_type="ADVERTISING_WAITLIST_AVAILABLE",
                        title="Advertising inventory is available",
                        body=(
                            "A requested advertising schedule is available. "
                            "Review it and reserve the slot."
                        ),
                        data={
                            "actionPath": "/dashboard/advertising",
                            "campaignId": str(entry.campaign_id),
                            "startAt": entry.start_at.isoformat(),
                        },
                    )
                    self._audit(
                        actor_id=None,
                        entity_type="waitlist",
                        entity_id=entry.id,
                        action="waitlist.notified",
                        after={"status": entry.status},
                    )
                    notified += 1
                    break
        return notified

    async def availability(
        self,
        *,
        placement_code: str,
        package_code: str,
        start_at: datetime,
        search_days: int = ALTERNATIVE_SEARCH_DAYS,
    ) -> AvailabilityView:
        start = _utc(start_at)
        if not 1 <= search_days <= 90:
            raise DomainError(
                code="ADVERTISING_INVALID_SEARCH_RANGE",
                message="Khoảng tìm lịch phải từ 1 đến 90 ngày.",
                status_code=422,
            )
        placement, package = await self._catalog_entry(placement_code, package_code)
        end = start + timedelta(hours=package.duration_hours)
        intervals = await self._active_intervals(
            placement.id,
            start,
            start + timedelta(days=search_days, hours=package.duration_hours),
        )
        fits, remaining = interval_capacity(
            capacity=placement.capacity,
            start_at=start,
            end_at=end,
            intervals=intervals,
        )
        alternatives = [
            start + timedelta(days=offset)
            for offset in range(1, search_days + 1)
            if interval_capacity(
                capacity=placement.capacity,
                start_at=start + timedelta(days=offset),
                end_at=start + timedelta(days=offset, hours=package.duration_hours),
                intervals=intervals,
            )[0]
        ][:5]
        return {
            "placement": placement,
            "package": package,
            "start_at": start,
            "end_at": end,
            "available": fits and placement.enabled and package.active,
            "remaining_slots": remaining if fits else 0,
            "alternatives": alternatives,
        }

    async def create_campaign(
        self,
        principal: AuthPrincipal,
        *,
        dossier_id: UUID,
        package_code: str,
        title: str,
        description: str,
        image_url: str | None,
        destination_url: str,
    ) -> AdvertisingCampaign:
        self._validate_url(destination_url)
        if image_url is not None:
            self._validate_url(image_url)
        async with self.session.begin():
            dossier = await self.session.scalar(
                select(Dossier).where(
                    Dossier.id == dossier_id,
                    Dossier.owner_user_id == principal.user_id,
                    Dossier.deleted_at.is_(None),
                )
            )
            if dossier is None or dossier.status in {
                DossierStatus.DRAFT,
                DossierStatus.REJECTED,
                DossierStatus.REVOKED,
                DossierStatus.CANCELLED,
            }:
                raise AdvertisingForbiddenError()
            placement, package = await self._catalog_entry_by_package(package_code)
            campaign = AdvertisingCampaign(
                owner_user_id=principal.user_id,
                dossier_id=dossier.id,
                package_id=package.id,
                placement_id=placement.id,
                purchase_context=(
                    "AFTER_PUBLICATION"
                    if dossier.status is DossierStatus.PUBLISHED
                    and dossier.visibility is DossierVisibility.PUBLIC
                    else "BEFORE_PUBLICATION"
                ),
                status="DRAFT",
                rotation_weight=package.rotation_weight,
            )
            self.session.add(campaign)
            await self.session.flush()
            creative = AdvertisingCreative(
                campaign_id=campaign.id,
                version=1,
                title=title.strip(),
                description=description.strip(),
                image_url=image_url,
                destination_url=destination_url,
                review_status="PENDING",
            )
            self.session.add(creative)
            self._audit(
                actor_id=principal.user_id,
                entity_type="campaign",
                entity_id=campaign.id,
                action="campaign.created",
                after={"dossier_id": str(dossier.id), "status": campaign.status},
            )
            await self.session.flush()
            return campaign

    async def submit_campaign(
        self, principal: AuthPrincipal, campaign_id: UUID
    ) -> AdvertisingCampaign:
        async with self.session.begin():
            campaign = await self._campaign(campaign_id, for_update=True)
            if campaign.owner_user_id != principal.user_id:
                raise AdvertisingForbiddenError()
            creative = await self.session.scalar(
                select(AdvertisingCreative)
                .where(AdvertisingCreative.campaign_id == campaign.id)
                .order_by(AdvertisingCreative.version.desc())
                .limit(1)
            )
            if campaign.status not in {"DRAFT", "REJECTED"} or creative is None:
                raise AdvertisingConflictError("Chiến dịch chưa thể gửi duyệt.")
            campaign.status = "PENDING_REVIEW"
            creative.review_status = "PENDING"
            creative.review_note = None
            self._audit(
                actor_id=principal.user_id,
                entity_type="campaign",
                entity_id=campaign.id,
                action="campaign.submitted",
                after={"status": campaign.status},
            )
            await self.session.flush()
            return campaign

    async def review_campaign(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        approve: bool | None = None,
        decision: str | None = None,
        reason: str | None = None,
    ) -> AdvertisingCampaign:
        self._require_admin(principal)
        if decision is None and approve is None:
            raise AdvertisingConflictError("A moderation decision is required.")
        normalized_decision = (decision or ("APPROVE" if approve else "REJECT")).upper()
        if normalized_decision not in {"APPROVE", "REJECT", "CHANGES_REQUESTED"}:
            raise AdvertisingConflictError("Unknown moderation decision.")
        async with self.session.begin():
            campaign = await self._campaign(campaign_id, for_update=True)
            if campaign.status != "PENDING_REVIEW":
                raise AdvertisingConflictError("Chiến dịch không chờ kiểm duyệt.")
            creative = await self.session.scalar(
                select(AdvertisingCreative)
                .where(AdvertisingCreative.campaign_id == campaign.id)
                .order_by(AdvertisingCreative.version.desc())
                .limit(1)
            )
            if creative is None:
                raise AdvertisingConflictError("Chiến dịch chưa có nội dung quảng cáo.")
            now = _utc(self.clock())
            approved = normalized_decision == "APPROVE"
            creative.review_status = (
                "APPROVED"
                if approved
                else "CHANGES_REQUESTED"
                if normalized_decision == "CHANGES_REQUESTED"
                else "REJECTED"
            )
            creative.review_note = reason.strip() if reason else None
            creative.reviewed_by_user_id = principal.user_id
            creative.approved_at = now if approved else None
            campaign.status = "APPROVED" if approved else "REJECTED"
            action = {
                "APPROVE": "campaign.approved",
                "REJECT": "campaign.rejected",
                "CHANGES_REQUESTED": "campaign.changes_requested",
            }[normalized_decision]
            self._audit(
                actor_id=principal.user_id,
                entity_type="campaign",
                entity_id=campaign.id,
                action=action,
                after={
                    "status": campaign.status,
                    "creative_id": str(creative.id),
                    "review_status": creative.review_status,
                    "review_note": creative.review_note,
                },
            )
            await self.session.flush()
            return campaign

    async def update_campaign_creative(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        title: str,
        description: str,
        image_url: str | None,
        destination_url: str,
    ) -> AdvertisingCreative:
        self._validate_url(destination_url)
        if image_url is not None:
            self._validate_url(image_url)
        async with self.session.begin():
            campaign = await self._campaign(campaign_id, for_update=True)
            if campaign.owner_user_id != principal.user_id:
                raise AdvertisingForbiddenError()
            if campaign.status not in {"DRAFT", "REJECTED"}:
                raise AdvertisingConflictError(
                    "Only an unsubmitted or returned campaign can be edited."
                )
            paid_order = await self.session.scalar(
                select(AdvertisingOrder.id).where(
                    AdvertisingOrder.campaign_id == campaign.id,
                    AdvertisingOrder.payment_status == "PAID",
                )
            )
            if paid_order is not None:
                raise AdvertisingConflictError(
                    "A paid campaign creative cannot be edited."
                )
            if len(title.strip()) < 2:
                raise AdvertisingConflictError("Creative title is too short.")
            latest = await self.session.scalar(
                select(func.max(AdvertisingCreative.version)).where(
                    AdvertisingCreative.campaign_id == campaign.id
                )
            )
            creative = AdvertisingCreative(
                campaign_id=campaign.id,
                version=(latest or 0) + 1,
                title=title.strip(),
                description=description.strip(),
                image_url=image_url,
                destination_url=destination_url.strip(),
                review_status="PENDING",
            )
            campaign.status = "DRAFT"
            self.session.add(creative)
            await self.session.flush()
            self._audit(
                actor_id=principal.user_id,
                entity_type="campaign",
                entity_id=campaign.id,
                action="creative.updated",
                after={
                    "creative_id": str(creative.id),
                    "version": creative.version,
                    "status": campaign.status,
                },
            )
            await self.session.flush()
            return creative

    async def reserve(
        self,
        principal: AuthPrincipal,
        *,
        campaign_id: UUID,
        start_at: datetime,
        idempotency_key: str,
        voucher_id: UUID | None = None,
    ) -> AdvertisingReservation:
        start = _utc(start_at)
        key = idempotency_key.strip()
        if not key or len(key) > 128:
            raise DomainError(
                code="ADVERTISING_INVALID_IDEMPOTENCY_KEY",
                message="Khóa yêu cầu không hợp lệ.",
                status_code=422,
            )

        async with self.session.begin():
            await self.session.scalar(
                select(User.id).where(User.id == principal.user_id).with_for_update()
            )
            replay: AdvertisingReservation | None = await self.session.scalar(
                select(AdvertisingReservation).where(
                    AdvertisingReservation.owner_user_id == principal.user_id,
                    AdvertisingReservation.idempotency_key == key,
                )
            )
            if replay is not None:
                if (
                    replay.campaign_id != campaign_id
                    or _db_utc(replay.start_at) != start
                ):
                    raise AdvertisingConflictError(
                        "Khóa yêu cầu đã được dùng cho một lịch khác."
                    )
                if replay.status != "HELD" or _db_utc(replay.expires_at) <= _utc(
                    self.clock()
                ):
                    raise AdvertisingConflictError(
                        "Lượt giữ chỗ đã hết hạn. Vui lòng kiểm tra lại lịch."
                    )
                saved_order = await self.session.scalar(
                    select(AdvertisingOrder).where(
                        AdvertisingOrder.reservation_id == replay.id
                    )
                )
                if saved_order is not None and saved_order.pricing_snapshot.get(
                    "voucherId"
                ) != (str(voucher_id) if voucher_id else None):
                    raise AdvertisingConflictError(
                        "Idempotency key belongs to a different voucher selection."
                    )
                return replay

            campaign = await self._campaign(campaign_id)
            if campaign.owner_user_id != principal.user_id:
                raise AdvertisingForbiddenError()
            placement = await self.session.scalar(
                select(AdvertisingPlacement)
                .where(AdvertisingPlacement.id == campaign.placement_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            replay = await self.session.scalar(
                select(AdvertisingReservation).where(
                    AdvertisingReservation.owner_user_id == principal.user_id,
                    AdvertisingReservation.idempotency_key == key,
                )
            )
            if replay is not None:
                if (
                    replay.campaign_id != campaign_id
                    or _db_utc(replay.start_at) != start
                ):
                    raise AdvertisingConflictError(
                        "Khóa yêu cầu đã được dùng cho một lịch khác."
                    )
                if replay.status != "HELD" or _db_utc(replay.expires_at) <= _utc(
                    self.clock()
                ):
                    raise AdvertisingConflictError(
                        "Lượt giữ chỗ đã hết hạn. Vui lòng kiểm tra lại lịch."
                    )
                saved_order = await self.session.scalar(
                    select(AdvertisingOrder).where(
                        AdvertisingOrder.reservation_id == replay.id
                    )
                )
                if saved_order is not None and saved_order.pricing_snapshot.get(
                    "voucherId"
                ) != (str(voucher_id) if voucher_id else None):
                    raise AdvertisingConflictError(
                        "Idempotency key belongs to a different voucher selection."
                    )
                return replay
            campaign = await self._campaign(campaign_id, for_update=True)
            if campaign.owner_user_id != principal.user_id:
                raise AdvertisingForbiddenError()
            if campaign.status != "APPROVED":
                raise AdvertisingConflictError(
                    "Quảng cáo cần được duyệt trước khi đặt lịch."
                )
            creative = await self.session.scalar(
                select(AdvertisingCreative).where(
                    AdvertisingCreative.campaign_id == campaign.id,
                    AdvertisingCreative.review_status == "APPROVED",
                )
            )
            if creative is None:
                raise AdvertisingConflictError("Nội dung quảng cáo chưa được duyệt.")
            package = await self.session.scalar(
                select(AdvertisingPackage)
                .where(AdvertisingPackage.id == campaign.package_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if placement is None or package is None:
                raise AdvertisingNotFoundError()
            if not placement.enabled or not package.active:
                raise AdvertisingConflictError("Vị trí hoặc gói quảng cáo đã đóng bán.")

            now = _utc(self.clock())
            if start < now:
                raise DomainError(
                    code="ADVERTISING_INVALID_START_TIME",
                    message="Ngày bắt đầu phải là hiện tại hoặc trong tương lai.",
                    status_code=422,
                )
            await self._expire_holds(placement.id, now)
            end = start + timedelta(hours=package.duration_hours)
            intervals = await self._active_intervals(placement.id, start, end)
            fits, _ = interval_capacity(
                capacity=placement.capacity,
                start_at=start,
                end_at=end,
                intervals=intervals,
            )
            if not fits:
                available = await self.availability(
                    placement_code=placement.code,
                    package_code=package.code,
                    start_at=start,
                )
                alternatives = [item.isoformat() for item in available["alternatives"]]
                raise AdvertisingConflictError(
                    "Vị trí này đã đủ quảng cáo trong khoảng thời gian bạn chọn.",
                    code="ADVERTISING_CAPACITY_FULL",
                    details={"availableDates": alternatives},
                )
            reservation = AdvertisingReservation(
                campaign_id=campaign.id,
                placement_id=placement.id,
                owner_user_id=principal.user_id,
                start_at=start,
                end_at=end,
                expires_at=now + self.reservation_ttl,
                status="HELD",
                idempotency_key=key,
            )
            campaign.status = "PENDING_PAYMENT"
            campaign.desired_start_at = start
            self.session.add(reservation)
            await self.session.flush()
            quote = await self._quote_for_user(
                principal.user_id,
                placement=placement,
                package=package,
                lock_policy=True,
            )
            order = AdvertisingOrder(
                reservation_id=reservation.id,
                campaign_id=campaign.id,
                package_id=package.id,
                user_id=principal.user_id,
                price_version=package.price_version,
                membership_tier=str(quote["membership_tier"]),
                membership_cycle_start=quote["membership_cycle_start"],
                discount_policy_version=int(quote["discount_policy_version"]),
                base_amount_vnd=int(quote["base_amount_vnd"]),
                discount_amount_vnd=int(quote["discount_amount_vnd"]),
                payable_amount_vnd=int(quote["payable_amount_vnd"]),
                payment_status="PENDING_PAYMENT",
                idempotency_key=key,
                allowance_expires_at=reservation.expires_at,
                pricing_snapshot={
                    "placementCode": placement.code,
                    "placementName": placement.name,
                    "packageCode": package.code,
                    "packageName": package.name,
                    "durationHours": package.duration_hours,
                    "baseAmountVnd": quote["base_amount_vnd"],
                    "discountAmountVnd": quote["discount_amount_vnd"],
                    "payableAmountVnd": quote["payable_amount_vnd"],
                    "priceVersion": package.price_version,
                    "membershipTier": quote["membership_tier"],
                    "discountPolicyVersion": quote["discount_policy_version"],
                },
            )
            self.session.add(order)
            await self.session.flush()
            if voucher_id is not None:
                from app.modules.promotions.checkout import PromotionCheckout

                held = await PromotionCheckout(self.session, now=now).reserve(
                    principal.user_id,
                    voucher_id,
                    order_reference=f"advertising:{order.id}",
                    service_code="ADVERTISING",
                    original_vnd=order.base_amount_vnd,
                    membership_discount_vnd=order.discount_amount_vnd,
                    product_id=str(package.id),
                    expires_at=reservation.expires_at,
                )
                order.discount_amount_vnd = held.discount_vnd
                order.payable_amount_vnd = held.payable_vnd
                order.pricing_snapshot = {
                    **order.pricing_snapshot,
                    "voucherId": str(voucher_id),
                    "voucherDiscountVnd": held.discount_vnd,
                    "membershipDiscountAppliedVnd": 0,
                    "discountAmountVnd": held.discount_vnd,
                    "payableAmountVnd": held.payable_vnd,
                }
            self._audit(
                actor_id=principal.user_id,
                entity_type="reservation",
                entity_id=reservation.id,
                action="reservation.held",
                after={
                    "campaign_id": str(campaign.id),
                    "placement_id": str(placement.id),
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat(),
                    "expires_at": reservation.expires_at.isoformat(),
                },
            )
            await self.session.flush()
            self._audit(
                actor_id=principal.user_id,
                entity_type="order",
                entity_id=order.id,
                action="order.quoted",
                after={
                    "campaign_id": str(campaign.id),
                    "base_amount_vnd": order.base_amount_vnd,
                    "discount_amount_vnd": order.discount_amount_vnd,
                    "payable_amount_vnd": order.payable_amount_vnd,
                    "membership_tier": order.membership_tier,
                },
            )
            return reservation

    async def get_reservation(
        self, principal: AuthPrincipal, reservation_id: UUID
    ) -> AdvertisingReservation:
        reservation = await self.session.scalar(
            select(AdvertisingReservation).where(
                AdvertisingReservation.id == reservation_id,
                AdvertisingReservation.owner_user_id == principal.user_id,
            )
        )
        if reservation is None:
            raise AdvertisingNotFoundError()
        return reservation

    async def get_order(
        self, principal: AuthPrincipal, order_id: UUID
    ) -> AdvertisingOrder:
        order = await self.session.scalar(
            select(AdvertisingOrder).where(
                AdvertisingOrder.id == order_id,
                AdvertisingOrder.user_id == principal.user_id,
            )
        )
        if order is None:
            raise AdvertisingNotFoundError()
        return order

    async def pay_order(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
        *,
        idempotency_key: str,
    ) -> AdvertisingOrder:
        key = idempotency_key.strip()
        if not key or len(key) > 128:
            raise DomainError(
                code="ADVERTISING_INVALID_IDEMPOTENCY_KEY",
                message="Khóa yêu cầu không hợp lệ.",
                status_code=422,
            )
        async with self.session.begin():
            order_ref = await self.session.scalar(
                select(AdvertisingOrder).where(
                    AdvertisingOrder.id == order_id,
                    AdvertisingOrder.user_id == principal.user_id,
                )
            )
            if order_ref is None:
                raise AdvertisingNotFoundError()
            reservation_ref = await self.session.get(
                AdvertisingReservation, order_ref.reservation_id
            )
            if reservation_ref is None:
                raise AdvertisingNotFoundError()

            await self.session.scalar(
                select(User.id).where(User.id == principal.user_id).with_for_update()
            )
            placement = await self.session.scalar(
                select(AdvertisingPlacement)
                .where(AdvertisingPlacement.id == reservation_ref.placement_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            reservation = await self.session.scalar(
                select(AdvertisingReservation)
                .where(AdvertisingReservation.id == reservation_ref.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            campaign = await self._campaign(order_ref.campaign_id, for_update=True)
            order = await self.session.scalar(
                select(AdvertisingOrder)
                .where(
                    AdvertisingOrder.id == order_id,
                    AdvertisingOrder.user_id == principal.user_id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if placement is None or reservation is None or order is None:
                raise AdvertisingNotFoundError()
            if order.payment_status == "PAID":
                if order.payment_idempotency_key != key:
                    raise AdvertisingConflictError("Đơn quảng cáo đã được thanh toán.")
                return order
            if order.payment_status != "PENDING_PAYMENT":
                raise AdvertisingConflictError(
                    "Đơn quảng cáo không còn chờ thanh toán."
                )
            now = _utc(self.clock())
            if (
                reservation.status != "HELD"
                or _db_utc(reservation.expires_at) <= now
                or _db_utc(order.allowance_expires_at) <= now
            ):
                raise AdvertisingConflictError(
                    "Lượt giữ chỗ đã hết hạn. Vui lòng kiểm tra lại lịch.",
                    code="ADVERTISING_RESERVATION_EXPIRED",
                )
            if campaign.status != "PENDING_PAYMENT":
                raise AdvertisingConflictError("Chiến dịch không còn chờ thanh toán.")
            dossier = await self.session.scalar(
                select(Dossier).where(
                    Dossier.id == campaign.dossier_id,
                    Dossier.owner_user_id == principal.user_id,
                )
            )
            if (
                dossier is None
                or dossier.deleted_at is not None
                or dossier.status in {DossierStatus.REVOKED, DossierStatus.CANCELLED}
            ):
                raise AdvertisingConflictError("Hồ sơ không còn đủ điều kiện quảng bá.")
            creative = await self.session.scalar(
                select(AdvertisingCreative).where(
                    AdvertisingCreative.campaign_id == campaign.id,
                    AdvertisingCreative.review_status == "APPROVED",
                )
            )
            if creative is None:
                raise AdvertisingConflictError("Nội dung quảng cáo chưa được duyệt.")

            posting: WalletJournal | None = None
            if order.payable_amount_vnd > 0:
                package_name = order.pricing_snapshot.get(
                    "packageName", "Gói quảng cáo"
                )
                posting = await WalletLedger(self.session).post(
                    user_id=principal.user_id,
                    delta=-order.payable_amount_vnd,
                    kind="PAYMENT",
                    key=f"advertising-order:{order.id}",
                    reference=f"advertising-order:{order.id}",
                    description=f"Thanh toán quảng cáo: {package_name}",
                )
            reservation.status = "CONFIRMED"
            campaign.status = "SCHEDULED"
            order.payment_status = "PAID"
            order.payment_idempotency_key = key
            order.wallet_transaction_id = posting.id if posting is not None else None
            order.paid_at = now
            if order.pricing_snapshot.get("voucherId"):
                from app.modules.promotions.checkout import PromotionCheckout

                await PromotionCheckout(self.session, now=now).redeem(
                    f"advertising:{order.id}"
                )
            booking = AdvertisingBooking(
                campaign_id=campaign.id,
                placement_id=placement.id,
                reservation_id=reservation.id,
                start_at=reservation.start_at,
                end_at=reservation.end_at,
                status="CONFIRMED",
                confirmed_at=now,
            )
            self.session.add(booking)
            self._audit(
                actor_id=principal.user_id,
                entity_type="order",
                entity_id=order.id,
                action="order.paid",
                after={
                    "payment_status": order.payment_status,
                    "wallet_transaction_id": (
                        str(posting.id) if posting is not None else None
                    ),
                    "booking_interval": [
                        reservation.start_at.isoformat(),
                        reservation.end_at.isoformat(),
                    ],
                },
            )
            await self.session.flush()
            return order

    async def expire_holds(self, *, limit: int = 500) -> int:
        now = _utc(self.clock())
        async with self.session.begin():
            placement_ids = list(
                await self.session.scalars(
                    select(AdvertisingReservation.placement_id)
                    .where(
                        AdvertisingReservation.status == "HELD",
                        AdvertisingReservation.expires_at <= now,
                    )
                    .distinct()
                    .order_by(AdvertisingReservation.placement_id)
                )
            )
            expired_count = 0
            for placement_id in placement_ids:
                await self.session.scalar(
                    select(AdvertisingPlacement.id)
                    .where(AdvertisingPlacement.id == placement_id)
                    .with_for_update()
                )
                expired = list(
                    await self.session.scalars(
                        select(AdvertisingReservation)
                        .where(
                            AdvertisingReservation.placement_id == placement_id,
                            AdvertisingReservation.status == "HELD",
                            AdvertisingReservation.expires_at <= now,
                        )
                        .order_by(AdvertisingReservation.expires_at)
                        .limit(max(limit - expired_count, 0))
                        .with_for_update(skip_locked=True)
                    )
                )
                for reservation in expired:
                    reservation.status = "EXPIRED"
                    order = await self.session.scalar(
                        select(AdvertisingOrder)
                        .where(
                            AdvertisingOrder.reservation_id == reservation.id,
                            AdvertisingOrder.payment_status == "PENDING_PAYMENT",
                        )
                        .with_for_update()
                    )
                    if order is not None:
                        order.payment_status = "EXPIRED"
                    campaign = await self._campaign(
                        reservation.campaign_id, for_update=True
                    )
                    if campaign.status == "PENDING_PAYMENT":
                        campaign.status = "APPROVED"
                    self._audit(
                        actor_id=None,
                        entity_type="reservation",
                        entity_id=reservation.id,
                        action="reservation.expired",
                        after={"status": "EXPIRED"},
                    )
                expired_count += len(expired)
                if expired_count >= limit:
                    break
            await self.session.flush()
            return expired_count

    async def _expire_holds(self, placement_id: UUID, now: datetime) -> None:
        expired = list(
            await self.session.scalars(
                select(AdvertisingReservation)
                .where(
                    AdvertisingReservation.placement_id == placement_id,
                    AdvertisingReservation.status == "HELD",
                    AdvertisingReservation.expires_at <= now,
                )
                .with_for_update()
            )
        )
        for reservation in expired:
            reservation.status = "EXPIRED"
            order = await self.session.scalar(
                select(AdvertisingOrder)
                .where(
                    AdvertisingOrder.reservation_id == reservation.id,
                    AdvertisingOrder.payment_status == "PENDING_PAYMENT",
                )
                .with_for_update()
            )
            if order is not None:
                order.payment_status = "EXPIRED"
                if order.pricing_snapshot.get("voucherId"):
                    from app.modules.promotions.checkout import PromotionCheckout

                    await PromotionCheckout(self.session, now=now).release(
                        f"advertising:{order.id}",
                        reason="Unpaid advertising hold expired",
                    )
            campaign = await self._campaign(reservation.campaign_id, for_update=True)
            if campaign.status == "PENDING_PAYMENT":
                campaign.status = "APPROVED"
            self._audit(
                actor_id=None,
                entity_type="reservation",
                entity_id=reservation.id,
                action="reservation.expired",
                after={"status": "EXPIRED"},
            )

    async def _active_intervals(
        self, placement_id: UUID, start_at: datetime, end_at: datetime
    ) -> list[Interval]:
        overlap_reservations = and_(
            AdvertisingReservation.placement_id == placement_id,
            AdvertisingReservation.start_at < end_at,
            AdvertisingReservation.end_at > start_at,
            or_(
                AdvertisingReservation.status == "PAYMENT_PROCESSING",
                and_(
                    AdvertisingReservation.status == "HELD",
                    AdvertisingReservation.expires_at > _utc(self.clock()),
                ),
            ),
        )
        reservations = list(
            await self.session.scalars(
                select(AdvertisingReservation).where(overlap_reservations)
            )
        )
        bookings = list(
            await self.session.scalars(
                select(AdvertisingBooking).where(
                    AdvertisingBooking.placement_id == placement_id,
                    AdvertisingBooking.status == "CONFIRMED",
                    AdvertisingBooking.start_at < end_at,
                    AdvertisingBooking.end_at > start_at,
                )
            )
        )
        return [(row.start_at, row.end_at) for row in reservations] + [
            (row.start_at, row.end_at) for row in bookings
        ]

    async def _quote_for_user(
        self,
        user_id: UUID,
        *,
        placement: AdvertisingPlacement,
        package: AdvertisingPackage,
        lock_policy: bool,
    ) -> QuoteView:
        from app.modules.memberships.models import UserMembership

        membership_query = select(UserMembership).where(
            UserMembership.user_id == user_id
        )
        if lock_policy:
            membership_query = membership_query.with_for_update()
        await self.session.scalar(membership_query)
        tier, cycle_start = await active_membership_cycle(self.session, user_id)
        if tier not in MEMBERSHIP_DISCOUNT_ALLOWANCE:
            raise DomainError(
                code="ADVERTISING_MEMBERSHIP_TIER_UNSUPPORTED",
                message="Cấp hội viên chưa được hỗ trợ cho ưu đãi quảng cáo.",
                status_code=409,
            )
        policy_query = select(AdvertisingDiscountPolicy).where(
            AdvertisingDiscountPolicy.tier == tier
        )
        if lock_policy:
            policy_query = policy_query.with_for_update()
        policy = await self.session.scalar(policy_query)
        if policy is None:
            raise DomainError(
                code="ADVERTISING_DISCOUNT_POLICY_MISSING",
                message="Chính sách ưu đãi quảng cáo chưa được cấu hình.",
                status_code=503,
            )
        now = _utc(self.clock())
        spent_rows = await self.session.scalars(
            select(AdvertisingOrder).where(
                AdvertisingOrder.user_id == user_id,
                AdvertisingOrder.membership_tier == tier,
                AdvertisingOrder.membership_cycle_start == cycle_start,
                or_(
                    AdvertisingOrder.payment_status == "PAID",
                    and_(
                        AdvertisingOrder.payment_status == "PENDING_PAYMENT",
                        AdvertisingOrder.allowance_expires_at > now,
                    ),
                ),
            )
        )
        spent = sum(
            0 if row.pricing_snapshot.get("voucherId") else row.discount_amount_vnd
            for row in spent_rows
        )
        allowance = policy.annual_allowance_vnd if policy.active else 0
        remaining_allowance = max(allowance - spent, 0)
        rate = policy.rate_basis_points if policy.active else 0
        base_amount = package.base_price_vnd
        raw_discount = (base_amount * rate + 5_000) // 10_000
        discount_amount = min(raw_discount, remaining_allowance, base_amount)
        return {
            "placement_code": placement.code,
            "placement_name": placement.name,
            "package_code": package.code,
            "package_name": package.name,
            "duration_hours": package.duration_hours,
            "membership_tier": tier,
            "membership_cycle_start": cycle_start,
            "discount_policy_version": policy.policy_version,
            "discount_rate_basis_points": rate,
            "remaining_discount_allowance_vnd": remaining_allowance,
            "base_amount_vnd": base_amount,
            "discount_amount_vnd": discount_amount,
            "payable_amount_vnd": base_amount - discount_amount,
            "price_version": package.price_version,
        }

    async def _committed_intervals(
        self, placement_id: UUID, now: datetime
    ) -> list[Interval]:
        reservations = list(
            await self.session.scalars(
                select(AdvertisingReservation).where(
                    AdvertisingReservation.placement_id == placement_id,
                    AdvertisingReservation.end_at > now,
                    or_(
                        AdvertisingReservation.status == "PAYMENT_PROCESSING",
                        and_(
                            AdvertisingReservation.status == "HELD",
                            AdvertisingReservation.expires_at > now,
                        ),
                    ),
                )
            )
        )
        bookings = list(
            await self.session.scalars(
                select(AdvertisingBooking).where(
                    AdvertisingBooking.placement_id == placement_id,
                    AdvertisingBooking.status == "CONFIRMED",
                    AdvertisingBooking.end_at > now,
                )
            )
        )
        return [(row.start_at, row.end_at) for row in reservations] + [
            (row.start_at, row.end_at) for row in bookings
        ]

    async def _catalog_entry(
        self, placement_code: str, package_code: str
    ) -> tuple[AdvertisingPlacement, AdvertisingPackage]:
        row = await self.session.execute(
            select(AdvertisingPlacement, AdvertisingPackage)
            .join(
                AdvertisingPackage,
                AdvertisingPackage.placement_id == AdvertisingPlacement.id,
            )
            .where(
                AdvertisingPlacement.code == placement_code,
                AdvertisingPackage.code == package_code,
                AdvertisingPackage.active.is_(True),
            )
        )
        result = row.one_or_none()
        if result is None:
            raise AdvertisingNotFoundError()
        return result[0], result[1]

    async def _catalog_entry_by_package(
        self, package_code: str
    ) -> tuple[AdvertisingPlacement, AdvertisingPackage]:
        row = await self.session.execute(
            select(AdvertisingPlacement, AdvertisingPackage)
            .join(
                AdvertisingPackage,
                AdvertisingPackage.placement_id == AdvertisingPlacement.id,
            )
            .where(
                AdvertisingPackage.code == package_code,
                AdvertisingPackage.active.is_(True),
                AdvertisingPlacement.enabled.is_(True),
            )
        )
        result = row.one_or_none()
        if result is None:
            raise AdvertisingNotFoundError()
        return result[0], result[1]

    async def _campaign(
        self, campaign_id: UUID, *, for_update: bool = False
    ) -> AdvertisingCampaign:
        query = select(AdvertisingCampaign).where(AdvertisingCampaign.id == campaign_id)
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        campaign = await self.session.scalar(query)
        if campaign is None:
            raise AdvertisingNotFoundError()
        return campaign

    def _audit(
        self,
        *,
        actor_id: UUID | None,
        entity_type: str,
        entity_id: UUID,
        action: str,
        before: Mapping[str, object] | None = None,
        after: Mapping[str, object],
    ) -> None:
        self.session.add(
            AdvertisingAuditLog(
                actor_user_id=actor_id,
                entity_type=entity_type,
                entity_id=str(entity_id),
                action=action,
                before_json=dict(before) if before is not None else None,
                after_json=dict(after),
                created_at=_utc(self.clock()),
            )
        )

    @staticmethod
    def _validate_url(value: str) -> None:
        from urllib.parse import urlsplit

        parsed = urlsplit(value.strip())
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            if (
                parsed.scheme != "https"
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise DomainError(
                    code="ADVERTISING_INVALID_URL",
                    message="Liên kết quảng cáo phải sử dụng HTTPS.",
                    status_code=422,
                )
            return
        if (
            value.startswith("/")
            and not value.startswith("//")
            and "\\" not in value
            and not any(ord(character) < 32 for character in value)
        ):
            return
        raise DomainError(
            code="ADVERTISING_INVALID_URL",
            message="Liên kết quảng cáo không hợp lệ.",
            status_code=422,
        )

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        if "SUPER_ADMIN" not in principal.roles:
            raise AdvertisingForbiddenError()
