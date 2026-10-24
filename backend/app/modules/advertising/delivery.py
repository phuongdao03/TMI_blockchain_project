import hashlib
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from typing import TypedDict, cast
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advertising.errors import (
    AdvertisingConflictError,
    AdvertisingForbiddenError,
    AdvertisingNotFoundError,
)
from app.modules.advertising.inventory import interval_capacity
from app.modules.advertising.models import (
    AdvertisingAuditLog,
    AdvertisingBooking,
    AdvertisingCampaign,
    AdvertisingCreative,
    AdvertisingDeliveryEvent,
    AdvertisingDeliveryStat,
    AdvertisingOrder,
    AdvertisingPlacement,
    AdvertisingReservation,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVisibility
from app.modules.notifications.service import NotificationService

TRAFFIC_TTL = timedelta(hours=24)
BOT_MARKERS = (
    "bot",
    "crawler",
    "spider",
    "slurp",
    "preview",
    "facebookexternalhit",
    "discordbot",
    "telegrambot",
    "linkedinbot",
    "pinterest",
    "bingpreview",
    "curl/",
    "wget/",
    "python-requests",
    "postmanruntime",
)


class DeliveryView(TypedDict):
    event_id: UUID
    placement_code: str
    title: str
    description: str
    image_url: str | None
    click_url: str


class CampaignMetricsView(TypedDict):
    campaign_id: UUID
    delivery_count: int
    valid_impressions: int
    valid_clicks: int
    ctr_basis_points: int
    actual_share_basis_points: int
    target_share_basis_points: int
    active_seconds: int


def select_weighted_round_robin(
    delivery_counts: Mapping[UUID, int], weights: Mapping[UUID, int]
) -> UUID:
    """Choose the campaign furthest below its weighted delivery target."""
    if not delivery_counts or delivery_counts.keys() != weights.keys():
        raise ValueError("Counts and positive weights must cover the same campaigns.")
    for campaign_id, count in delivery_counts.items():
        if count < 0 or weights[campaign_id] < 1:
            raise ValueError(
                "Delivery counts must be nonnegative and weights positive."
            )
    return min(
        delivery_counts,
        key=lambda campaign_id: (
            Fraction(delivery_counts[campaign_id], weights[campaign_id]),
            campaign_id.hex,
        ),
    )


def is_valid_ad_traffic(user_agent: str | None) -> bool:
    normalized = (user_agent or "").strip().lower()
    return bool(normalized) and not any(marker in normalized for marker in BOT_MARKERS)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AdvertisingDeliveryService:
    def __init__(
        self, session: AsyncSession, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        self.session = session
        self.clock = clock or (lambda: datetime.now(UTC))

    async def select_ad(
        self, placement_code: str, *, user_agent: str | None
    ) -> DeliveryView | None:
        if not is_valid_ad_traffic(user_agent):
            return None
        now = _utc(self.clock())
        async with self.session.begin():
            placement = await self.session.scalar(
                select(AdvertisingPlacement)
                .where(AdvertisingPlacement.code == placement_code)
                .with_for_update()
            )
            if placement is None:
                return None

            latest_version = (
                select(func.max(AdvertisingCreative.version))
                .where(AdvertisingCreative.campaign_id == AdvertisingCampaign.id)
                .correlate(AdvertisingCampaign)
                .scalar_subquery()
            )
            paid_order_exists = (
                select(AdvertisingOrder.id)
                .where(
                    AdvertisingOrder.campaign_id == AdvertisingCampaign.id,
                    AdvertisingOrder.payment_status == "PAID",
                )
                .exists()
            )
            rows = (
                await self.session.execute(
                    select(
                        AdvertisingCampaign,
                        AdvertisingCreative,
                        AdvertisingBooking,
                    )
                    .join(
                        AdvertisingBooking,
                        AdvertisingBooking.campaign_id == AdvertisingCampaign.id,
                    )
                    .join(
                        AdvertisingCreative,
                        and_(
                            AdvertisingCreative.campaign_id == AdvertisingCampaign.id,
                            AdvertisingCreative.version == latest_version,
                            AdvertisingCreative.review_status == "APPROVED",
                        ),
                    )
                    .join(Dossier, Dossier.id == AdvertisingCampaign.dossier_id)
                    .where(
                        AdvertisingCampaign.placement_id == placement.id,
                        AdvertisingCampaign.status == "ACTIVE",
                        AdvertisingCampaign.actual_start_at <= now,
                        AdvertisingCampaign.actual_end_at > now,
                        AdvertisingBooking.status == "CONFIRMED",
                        AdvertisingBooking.start_at <= now,
                        AdvertisingBooking.end_at > now,
                        paid_order_exists,
                        Dossier.status == DossierStatus.PUBLISHED,
                        Dossier.visibility == DossierVisibility.PUBLIC,
                        Dossier.deleted_at.is_(None),
                    )
                    .order_by(AdvertisingCampaign.id)
                )
            ).all()
            if not rows:
                return None

            campaigns = [row[0] for row in rows]
            weights = {
                campaign.id: (
                    campaign.rotation_weight
                    if placement.delivery_mode == "WEIGHTED_ROTATION"
                    else 1
                )
                for campaign in campaigns
            }
            pool_signature = "|".join(
                [placement.delivery_mode]
                + [
                    f"{campaign.id.hex}:{weights[campaign.id]}"
                    for campaign in sorted(campaigns, key=lambda item: item.id.hex)
                ]
            )
            pool_key = hashlib.sha256(pool_signature.encode("ascii")).hexdigest()
            if placement.rotation_pool_key != pool_key:
                for campaign in campaigns:
                    campaign.rotation_count = 0
                placement.rotation_pool_key = pool_key
            counts = {campaign.id: campaign.rotation_count for campaign in campaigns}
            selected_id = select_weighted_round_robin(counts, weights)
            campaign, creative, _ = next(
                row for row in rows if row[0].id == selected_id
            )
            campaign.rotation_count += 1
            campaign.delivery_count += 1
            event = AdvertisingDeliveryEvent(
                id=uuid4(),
                campaign_id=campaign.id,
                placement_id=placement.id,
                destination_url=creative.destination_url,
                selected_at=now,
                valid_traffic=True,
            )
            self.session.add(event)
            stat = await self._stat(campaign.id, placement.id, now.date())
            stat.delivery_count += 1
            await self.session.flush()
            return {
                "event_id": event.id,
                "placement_code": placement.code,
                "title": creative.title,
                "description": creative.description,
                "image_url": creative.image_url,
                "click_url": f"/api/v1/advertising/delivery/{event.id}/click",
            }

    async def record_impression(
        self, event_id: UUID, *, user_agent: str | None
    ) -> bool:
        if not is_valid_ad_traffic(user_agent):
            return False
        now = _utc(self.clock())
        async with self.session.begin():
            event = await self.session.scalar(
                select(AdvertisingDeliveryEvent)
                .where(AdvertisingDeliveryEvent.id == event_id)
                .with_for_update()
            )
            if (
                event is None
                or not event.valid_traffic
                or event.impression_at is not None
                or now - _utc(event.selected_at) > TRAFFIC_TTL
            ):
                return False
            event.impression_at = now
            stat = await self._stat(
                event.campaign_id, event.placement_id, _utc(event.selected_at).date()
            )
            stat.valid_impressions += 1
            return True

    async def record_click(
        self, event_id: UUID, *, user_agent: str | None
    ) -> str | None:
        if not is_valid_ad_traffic(user_agent):
            return None
        now = _utc(self.clock())
        async with self.session.begin():
            event = await self.session.scalar(
                select(AdvertisingDeliveryEvent)
                .where(AdvertisingDeliveryEvent.id == event_id)
                .with_for_update()
            )
            if (
                event is None
                or not event.valid_traffic
                or now - _utc(event.selected_at) > TRAFFIC_TTL
            ):
                return None
            if event.clicked_at is None:
                event.clicked_at = now
                stat = await self._stat(
                    event.campaign_id,
                    event.placement_id,
                    _utc(event.selected_at).date(),
                )
                stat.valid_clicks += 1
            return event.destination_url

    async def campaign_metrics(
        self, principal: AuthPrincipal, campaign_id: UUID
    ) -> CampaignMetricsView:
        campaign = await self.session.scalar(
            select(AdvertisingCampaign).where(AdvertisingCampaign.id == campaign_id)
        )
        if campaign is None:
            raise AdvertisingNotFoundError()
        if (
            campaign.owner_user_id != principal.user_id
            and "SUPER_ADMIN" not in principal.roles
        ):
            raise AdvertisingForbiddenError()
        rows = list(
            await self.session.scalars(
                select(AdvertisingDeliveryStat).where(
                    AdvertisingDeliveryStat.campaign_id == campaign.id
                )
            )
        )
        delivery_count = sum(row.delivery_count for row in rows)
        impressions = sum(row.valid_impressions for row in rows)
        clicks = sum(row.valid_clicks for row in rows)
        placement = await self.session.get(AdvertisingPlacement, campaign.placement_id)
        peers = list(
            await self.session.scalars(
                select(AdvertisingCampaign).where(
                    AdvertisingCampaign.placement_id == campaign.placement_id,
                    AdvertisingCampaign.status == "ACTIVE",
                    AdvertisingCampaign.actual_start_at.is_not(None),
                    AdvertisingCampaign.actual_end_at > _utc(self.clock()),
                )
            )
        )
        weighted = (
            placement is not None and placement.delivery_mode == "WEIGHTED_ROTATION"
        )
        peer_weights = {
            peer.id: peer.rotation_weight if weighted else 1 for peer in peers
        }
        weights = list(peer_weights.values()) or [1]
        weight = peer_weights.get(campaign.id, 1)
        active_delivery_count = campaign.rotation_count
        pool_deliveries = sum(peer.rotation_count for peer in peers)
        actual_share = (
            (active_delivery_count * 10_000 + pool_deliveries // 2) // pool_deliveries
            if pool_deliveries
            else 0
        )
        target_share = (
            (weight * 10_000 + sum(weights) // 2) // sum(weights)
            if campaign.id in peer_weights
            else 0
        )
        active_until = min(
            _utc(self.clock()), _utc(campaign.actual_end_at or self.clock())
        )
        active_seconds = (
            max(0, int((active_until - _utc(campaign.actual_start_at)).total_seconds()))
            if campaign.actual_start_at is not None
            else 0
        )
        return {
            "campaign_id": campaign.id,
            "delivery_count": delivery_count,
            "valid_impressions": impressions,
            "valid_clicks": clicks,
            "ctr_basis_points": (clicks * 10_000 + impressions // 2) // impressions
            if impressions
            else 0,
            "actual_share_basis_points": actual_share,
            "target_share_basis_points": target_share,
            "active_seconds": active_seconds,
        }

    async def advance_lifecycle(self, *, limit: int = 500) -> int:
        now = _utc(self.clock())
        async with self.session.begin():
            placement_ids = list(
                await self.session.scalars(
                    select(AdvertisingCampaign.placement_id)
                    .where(
                        AdvertisingCampaign.status.in_(
                            ("SCHEDULED", "ACTIVE", "PAUSED")
                        ),
                        (AdvertisingCampaign.status.in_(("ACTIVE", "PAUSED")))
                        | (AdvertisingCampaign.desired_start_at <= now),
                    )
                    .distinct()
                    .order_by(AdvertisingCampaign.placement_id)
                    .limit(limit)
                )
            )
        changed = 0
        for placement_id in placement_ids:
            async with self.session.begin():
                placement = await self.session.scalar(
                    select(AdvertisingPlacement)
                    .where(AdvertisingPlacement.id == placement_id)
                    .with_for_update()
                )
                if placement is None:
                    continue
                rows = (
                    await self.session.execute(
                        select(
                            AdvertisingCampaign,
                            AdvertisingBooking,
                            AdvertisingOrder,
                            Dossier,
                        )
                        .join(
                            AdvertisingBooking,
                            AdvertisingBooking.campaign_id == AdvertisingCampaign.id,
                        )
                        .join(
                            AdvertisingOrder,
                            and_(
                                AdvertisingOrder.campaign_id == AdvertisingCampaign.id,
                                AdvertisingOrder.payment_status == "PAID",
                            ),
                        )
                        .join(Dossier, Dossier.id == AdvertisingCampaign.dossier_id)
                        .where(
                            AdvertisingCampaign.placement_id == placement.id,
                            AdvertisingCampaign.status.in_(
                                ("SCHEDULED", "ACTIVE", "PAUSED")
                            ),
                            (AdvertisingCampaign.status.in_(("ACTIVE", "PAUSED")))
                            | (AdvertisingCampaign.desired_start_at <= now),
                            AdvertisingBooking.status == "CONFIRMED",
                        )
                        .order_by(AdvertisingCampaign.id)
                        .limit(limit)
                    )
                ).all()
                for campaign, booking, order, dossier in rows:
                    if campaign.status in {"ACTIVE", "PAUSED"}:
                        actual_end = campaign.actual_end_at
                        if actual_end is None or _utc(actual_end) > now:
                            continue
                        campaign.status = "COMPLETED"
                        booking.status = "COMPLETED"
                        self._audit_lifecycle(
                            campaign.id,
                            "campaign.completed",
                            {"status": "COMPLETED", "actual_end_at": now.isoformat()},
                        )
                        await self._notify_owner(
                            campaign,
                            event="completed",
                            title="Advertising campaign completed",
                            body="Your booked advertising period has ended.",
                            event_time=now,
                        )
                        changed += 1
                        continue

                    if _utc(booking.start_at) > now:
                        continue
                    if _utc(booking.end_at) <= now:
                        campaign.status = "NEEDS_RESCHEDULE"
                        self._audit_lifecycle(
                            campaign.id,
                            "campaign.needs_reschedule",
                            {"reason": "booking_window_elapsed"},
                        )
                        await self._notify_owner(
                            campaign,
                            event="reschedule",
                            title="Advertising schedule needs attention",
                            body=(
                                "The booked schedule passed before delivery could "
                                "start. Choose a new date."
                            ),
                            event_time=now,
                        )
                        changed += 1
                        continue
                    if not (
                        dossier.status == DossierStatus.PUBLISHED
                        and dossier.visibility == DossierVisibility.PUBLIC
                        and dossier.deleted_at is None
                    ):
                        continue
                    creative = await self._approved_current_creative(campaign.id)
                    if creative is None:
                        continue

                    actual_end = now + timedelta(hours=self._paid_duration_hours(order))
                    fits, _ = await self._capacity_for_campaign(
                        placement,
                        campaign.id,
                        start_at=now,
                        end_at=actual_end,
                        now=now,
                    )
                    if not fits:
                        campaign.status = "NEEDS_RESCHEDULE"
                        self._audit_lifecycle(
                            campaign.id,
                            "campaign.needs_reschedule",
                            {"reason": "full_duration_unavailable"},
                        )
                        changed += 1
                        continue
                    before = {
                        "start_at": booking.start_at.isoformat(),
                        "end_at": booking.end_at.isoformat(),
                        "status": campaign.status,
                    }
                    booking.start_at = now
                    booking.end_at = actual_end
                    campaign.actual_start_at = now
                    campaign.actual_end_at = actual_end
                    campaign.status = "ACTIVE"
                    self._audit_lifecycle(
                        campaign.id,
                        "campaign.started",
                        {
                            "before": before,
                            "start_at": now.isoformat(),
                            "end_at": actual_end.isoformat(),
                        },
                    )
                    await self._notify_owner(
                        campaign,
                        event="started",
                        title="Advertising campaign started",
                        body=(
                            "Your approved advertisement is now eligible for rotation."
                        ),
                        event_time=now,
                    )
                    changed += 1
        return changed

    async def reschedule_campaign(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        start_at: datetime,
    ) -> AdvertisingCampaign:
        start = _utc(start_at)
        now = _utc(self.clock())
        if start < now:
            raise AdvertisingConflictError(
                "A reschedule must start in the future.",
                code="ADVERTISING_INVALID_START_TIME",
            )
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
            campaign = await self.session.scalar(
                select(AdvertisingCampaign)
                .where(AdvertisingCampaign.id == campaign_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            booking = await self.session.scalar(
                select(AdvertisingBooking)
                .where(AdvertisingBooking.campaign_id == campaign_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            order = await self.session.scalar(
                select(AdvertisingOrder)
                .where(
                    AdvertisingOrder.campaign_id == campaign_id,
                    AdvertisingOrder.payment_status == "PAID",
                )
                .order_by(AdvertisingOrder.paid_at.desc())
                .limit(1)
            )
            if (
                placement is None
                or campaign is None
                or booking is None
                or order is None
            ):
                raise AdvertisingNotFoundError()
            if campaign.status != "NEEDS_RESCHEDULE":
                raise AdvertisingConflictError(
                    "Campaign is not waiting for a new schedule."
                )
            if booking.status != "CONFIRMED":
                raise AdvertisingConflictError(
                    "Only a paid confirmed booking can be rescheduled."
                )
            end = start + timedelta(hours=self._paid_duration_hours(order))
            fits, _ = await self._capacity_for_campaign(
                placement,
                campaign.id,
                start_at=start,
                end_at=end,
                now=now,
            )
            if not fits:
                raise AdvertisingConflictError(
                    "The requested interval has no available capacity."
                )
            before = {
                "start_at": booking.start_at.isoformat(),
                "end_at": booking.end_at.isoformat(),
                "status": campaign.status,
            }
            booking.start_at = start
            booking.end_at = end
            campaign.desired_start_at = start
            campaign.actual_start_at = None
            campaign.actual_end_at = None
            campaign.status = "SCHEDULED"
            self._audit_lifecycle(
                campaign.id,
                "campaign.rescheduled",
                {
                    "before": before,
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat(),
                },
                actor_id=principal.user_id,
            )
            await self.session.flush()
            return campaign

    async def _capacity_for_campaign(
        self,
        placement: AdvertisingPlacement,
        campaign_id: UUID,
        *,
        start_at: datetime,
        end_at: datetime,
        now: datetime,
    ) -> tuple[bool, int]:
        bookings = (
            await self.session.execute(
                select(AdvertisingBooking.start_at, AdvertisingBooking.end_at).where(
                    AdvertisingBooking.placement_id == placement.id,
                    AdvertisingBooking.campaign_id != campaign_id,
                    AdvertisingBooking.status == "CONFIRMED",
                    AdvertisingBooking.start_at < end_at,
                    AdvertisingBooking.end_at > start_at,
                )
            )
        ).all()
        holds = (
            await self.session.execute(
                select(
                    AdvertisingReservation.start_at,
                    AdvertisingReservation.end_at,
                ).where(
                    AdvertisingReservation.placement_id == placement.id,
                    AdvertisingReservation.status.in_(("HELD", "PAYMENT_PROCESSING")),
                    AdvertisingReservation.expires_at > now,
                    AdvertisingReservation.start_at < end_at,
                    AdvertisingReservation.end_at > start_at,
                )
            )
        ).all()
        return interval_capacity(
            capacity=placement.capacity,
            start_at=start_at,
            end_at=end_at,
            intervals=[(row[0], row[1]) for row in [*bookings, *holds]],
        )

    async def _approved_current_creative(
        self, campaign_id: UUID
    ) -> AdvertisingCreative | None:
        latest_version = await self.session.scalar(
            select(func.max(AdvertisingCreative.version)).where(
                AdvertisingCreative.campaign_id == campaign_id
            )
        )
        if latest_version is None:
            return None
        return cast(
            AdvertisingCreative | None,
            await self.session.scalar(
                select(AdvertisingCreative).where(
                    AdvertisingCreative.campaign_id == campaign_id,
                    AdvertisingCreative.version == latest_version,
                    AdvertisingCreative.review_status == "APPROVED",
                )
            ),
        )

    @staticmethod
    def _paid_duration_hours(order: AdvertisingOrder) -> int:
        duration = order.pricing_snapshot.get("durationHours")
        if isinstance(duration, int) and duration > 0:
            return duration
        raise AdvertisingConflictError(
            "Paid order is missing its duration snapshot.",
            code="ADVERTISING_INVALID_ORDER_SNAPSHOT",
        )

    def _audit_lifecycle(
        self,
        campaign_id: UUID,
        action: str,
        after: dict[str, object],
        *,
        actor_id: UUID | None = None,
    ) -> None:
        self.session.add(
            AdvertisingAuditLog(
                actor_user_id=actor_id,
                entity_type="campaign",
                entity_id=str(campaign_id),
                action=action,
                before_json=None,
                after_json=after,
                created_at=_utc(self.clock()),
            )
        )

    async def _notify_owner(
        self,
        campaign: AdvertisingCampaign,
        *,
        event: str,
        title: str,
        body: str,
        event_time: datetime,
    ) -> None:
        event_id = uuid5(
            NAMESPACE_URL,
            f"advertising:{campaign.id}:{event}:{event_time.isoformat()}",
        )
        await NotificationService(self.session).consume_in_transaction(
            event_id=event_id,
            user_id=campaign.owner_user_id,
            event_type=f"ADVERTISING_CAMPAIGN_{event.upper()}",
            title=title,
            body=body,
            data={
                "actionPath": "/dashboard/advertising",
                "campaignId": str(campaign.id),
            },
        )

    async def _stat(
        self, campaign_id: UUID, placement_id: UUID, stat_date: date
    ) -> AdvertisingDeliveryStat:
        stat = await self.session.scalar(
            select(AdvertisingDeliveryStat)
            .where(
                AdvertisingDeliveryStat.campaign_id == campaign_id,
                AdvertisingDeliveryStat.stat_date == stat_date,
            )
            .with_for_update()
        )
        if stat is None:
            stat = AdvertisingDeliveryStat(
                campaign_id=campaign_id,
                placement_id=placement_id,
                stat_date=stat_date,
            )
            self.session.add(stat)
            await self.session.flush()
        return stat
