from collections import defaultdict
from datetime import UTC, date, datetime, time
from typing import TypedDict
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advertising.errors import AdvertisingForbiddenError
from app.modules.advertising.models import (
    AdvertisingBooking,
    AdvertisingCampaign,
    AdvertisingCreative,
    AdvertisingDeliveryStat,
    AdvertisingOrder,
    AdvertisingPackage,
    AdvertisingPlacement,
    AdvertisingReservation,
)
from app.modules.auth.models import User
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Dossier


class InventoryItem(TypedDict):
    id: UUID
    campaign_id: UUID
    owner_email: str
    dossier_code: str
    dossier_title: str
    status: str
    payment_status: str | None
    start_at: datetime
    end_at: datetime
    expires_at: datetime | None


class AdminPlacementInventory(TypedDict):
    id: UUID
    code: str
    name: str
    page_location: str
    delivery_mode: str
    capacity: int
    enabled: bool
    bookings: list[InventoryItem]
    reservations: list[InventoryItem]


class CampaignDistribution(TypedDict):
    campaign_id: UUID
    title: str | None
    delivery_count: int
    valid_impressions: int
    valid_clicks: int
    target_share_basis_points: int
    actual_share_basis_points: int


class PlacementReport(TypedDict):
    placement_id: UUID
    placement_code: str
    placement_name: str
    paid_orders: int
    paid_revenue_vnd: int
    delivery_count: int
    valid_impressions: int
    valid_clicks: int
    ctr_basis_points: int
    campaigns: list[CampaignDistribution]


class CampaignReviewItem(TypedDict):
    campaign_id: UUID
    owner_email: str
    dossier_id: UUID
    dossier_code: str
    dossier_title: str
    placement_code: str
    package_name: str
    campaign_status: str
    creative_id: UUID
    creative_version: int
    title: str
    description: str
    image_url: str | None
    destination_url: str
    review_status: str


class AdvertisingAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def campaign_review_queue(
        self, principal: AuthPrincipal, *, limit: int = 200
    ) -> list[CampaignReviewItem]:
        self._require_admin(principal)
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
                    User,
                    Dossier,
                    AdvertisingPlacement,
                    AdvertisingPackage,
                    AdvertisingCreative,
                )
                .join(User, User.id == AdvertisingCampaign.owner_user_id)
                .join(Dossier, Dossier.id == AdvertisingCampaign.dossier_id)
                .join(
                    AdvertisingPlacement,
                    AdvertisingPlacement.id == AdvertisingCampaign.placement_id,
                )
                .join(
                    AdvertisingPackage,
                    AdvertisingPackage.id == AdvertisingCampaign.package_id,
                )
                .join(
                    AdvertisingCreative,
                    and_(
                        AdvertisingCreative.campaign_id == AdvertisingCampaign.id,
                        AdvertisingCreative.version == latest_version,
                    ),
                )
                .where(AdvertisingCampaign.status == "PENDING_REVIEW")
                .order_by(AdvertisingCampaign.created_at)
                .limit(limit)
            )
        ).all()
        return [
            {
                "campaign_id": campaign.id,
                "owner_email": user.email,
                "dossier_id": dossier.id,
                "dossier_code": dossier.code,
                "dossier_title": dossier.title,
                "placement_code": placement.code,
                "package_name": package.name,
                "campaign_status": campaign.status,
                "creative_id": creative.id,
                "creative_version": creative.version,
                "title": creative.title,
                "description": creative.description,
                "image_url": creative.image_url,
                "destination_url": creative.destination_url,
                "review_status": creative.review_status,
            }
            for campaign, user, dossier, placement, package, creative in rows
        ]

    async def inventory(
        self,
        principal: AuthPrincipal,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> list[AdminPlacementInventory]:
        self._require_admin(principal)
        placements = list(
            await self.session.scalars(
                select(AdvertisingPlacement).order_by(AdvertisingPlacement.name)
            )
        )
        booking_rows = (
            await self.session.execute(
                select(
                    AdvertisingBooking,
                    AdvertisingCampaign,
                    User,
                    Dossier,
                    AdvertisingOrder.payment_status,
                )
                .join(
                    AdvertisingCampaign,
                    AdvertisingCampaign.id == AdvertisingBooking.campaign_id,
                )
                .join(User, User.id == AdvertisingCampaign.owner_user_id)
                .join(Dossier, Dossier.id == AdvertisingCampaign.dossier_id)
                .outerjoin(
                    AdvertisingOrder,
                    AdvertisingOrder.reservation_id
                    == AdvertisingBooking.reservation_id,
                )
                .where(
                    AdvertisingBooking.start_at < end_at,
                    AdvertisingBooking.end_at > start_at,
                    AdvertisingBooking.status.in_(("CONFIRMED", "COMPLETED")),
                )
                .order_by(AdvertisingBooking.start_at)
            )
        ).all()
        reservation_rows = (
            await self.session.execute(
                select(
                    AdvertisingReservation,
                    AdvertisingCampaign,
                    User,
                    Dossier,
                    AdvertisingOrder.payment_status,
                )
                .join(
                    AdvertisingCampaign,
                    AdvertisingCampaign.id == AdvertisingReservation.campaign_id,
                )
                .join(User, User.id == AdvertisingReservation.owner_user_id)
                .join(Dossier, Dossier.id == AdvertisingCampaign.dossier_id)
                .outerjoin(
                    AdvertisingOrder,
                    AdvertisingOrder.reservation_id == AdvertisingReservation.id,
                )
                .where(
                    AdvertisingReservation.start_at < end_at,
                    AdvertisingReservation.end_at > start_at,
                    AdvertisingReservation.status.in_(("HELD", "PAYMENT_PROCESSING")),
                )
                .order_by(AdvertisingReservation.start_at)
            )
        ).all()
        booking_map: dict[UUID, list[InventoryItem]] = defaultdict(list)
        reservation_map: dict[UUID, list[InventoryItem]] = defaultdict(list)
        for booking, campaign, user, dossier, payment_status in booking_rows:
            booking_map[booking.placement_id].append(
                {
                    "id": booking.id,
                    "campaign_id": campaign.id,
                    "owner_email": user.email,
                    "dossier_code": dossier.code,
                    "dossier_title": dossier.title,
                    "status": booking.status,
                    "payment_status": payment_status,
                    "start_at": booking.start_at,
                    "end_at": booking.end_at,
                    "expires_at": None,
                }
            )
        for reservation, campaign, user, dossier, payment_status in reservation_rows:
            reservation_map[reservation.placement_id].append(
                {
                    "id": reservation.id,
                    "campaign_id": campaign.id,
                    "owner_email": user.email,
                    "dossier_code": dossier.code,
                    "dossier_title": dossier.title,
                    "status": reservation.status,
                    "payment_status": payment_status,
                    "start_at": reservation.start_at,
                    "end_at": reservation.end_at,
                    "expires_at": reservation.expires_at,
                }
            )
        return [
            {
                "id": placement.id,
                "code": placement.code,
                "name": placement.name,
                "page_location": placement.page_location,
                "delivery_mode": placement.delivery_mode,
                "capacity": placement.capacity,
                "enabled": placement.enabled,
                "bookings": booking_map[placement.id],
                "reservations": reservation_map[placement.id],
            }
            for placement in placements
        ]

    async def reports(
        self,
        principal: AuthPrincipal,
        *,
        start_date: date,
        end_date: date,
    ) -> list[PlacementReport]:
        self._require_admin(principal)
        if start_date >= end_date:
            raise ValueError("Report end date must be after start date.")
        placements = list(
            await self.session.scalars(
                select(AdvertisingPlacement).order_by(AdvertisingPlacement.name)
            )
        )
        stats_rows = (
            await self.session.execute(
                select(
                    AdvertisingDeliveryStat.placement_id,
                    AdvertisingDeliveryStat.campaign_id,
                    func.sum(AdvertisingDeliveryStat.delivery_count),
                    func.sum(AdvertisingDeliveryStat.valid_impressions),
                    func.sum(AdvertisingDeliveryStat.valid_clicks),
                )
                .where(
                    AdvertisingDeliveryStat.stat_date >= start_date,
                    AdvertisingDeliveryStat.stat_date < end_date,
                )
                .group_by(
                    AdvertisingDeliveryStat.placement_id,
                    AdvertisingDeliveryStat.campaign_id,
                )
            )
        ).all()
        orders_rows = (
            await self.session.execute(
                select(
                    AdvertisingCampaign.placement_id,
                    func.count(AdvertisingOrder.id),
                    func.sum(AdvertisingOrder.payable_amount_vnd),
                )
                .join(
                    AdvertisingCampaign,
                    AdvertisingCampaign.id == AdvertisingOrder.campaign_id,
                )
                .where(
                    AdvertisingOrder.payment_status == "PAID",
                    AdvertisingOrder.paid_at
                    >= datetime.combine(start_date, time.min, tzinfo=UTC),
                    AdvertisingOrder.paid_at
                    < datetime.combine(end_date, time.min, tzinfo=UTC),
                )
                .group_by(AdvertisingCampaign.placement_id)
            )
        ).all()
        latest_version = (
            select(func.max(AdvertisingCreative.version))
            .where(AdvertisingCreative.campaign_id == AdvertisingCampaign.id)
            .correlate(AdvertisingCampaign)
            .scalar_subquery()
        )
        campaigns = (
            await self.session.execute(
                select(
                    AdvertisingCampaign,
                    AdvertisingCreative.title,
                )
                .outerjoin(
                    AdvertisingCreative,
                    and_(
                        AdvertisingCreative.campaign_id == AdvertisingCampaign.id,
                        AdvertisingCreative.version == latest_version,
                    ),
                )
                .where(
                    AdvertisingCampaign.actual_start_at
                    < datetime.combine(end_date, time.min, tzinfo=UTC),
                    AdvertisingCampaign.actual_end_at
                    > datetime.combine(start_date, time.min, tzinfo=UTC),
                )
            )
        ).all()
        stat_map = {
            (placement_id, campaign_id): {
                "delivery_count": int(deliveries or 0),
                "valid_impressions": int(impressions or 0),
                "valid_clicks": int(clicks or 0),
            }
            for placement_id, campaign_id, deliveries, impressions, clicks in stats_rows
        }
        order_map = {
            placement_id: (int(order_count or 0), int(revenue or 0))
            for placement_id, order_count, revenue in orders_rows
        }
        campaigns_by_placement: dict[
            UUID, list[tuple[AdvertisingCampaign, str | None]]
        ] = defaultdict(list)
        for campaign, title in campaigns:
            campaigns_by_placement[campaign.placement_id].append((campaign, title))
        result: list[PlacementReport] = []
        for placement in placements:
            peer_campaigns = campaigns_by_placement[placement.id]
            weights = {
                campaign.id: (
                    campaign.rotation_weight
                    if placement.delivery_mode == "WEIGHTED_ROTATION"
                    else 1
                )
                for campaign, _ in peer_campaigns
            }
            total_weight = sum(weights.values())
            total_deliveries = sum(
                stat_map.get((placement.id, campaign.id), {}).get("delivery_count", 0)
                for campaign, _ in peer_campaigns
            )
            campaign_reports: list[CampaignDistribution] = []
            delivery_total = impression_total = click_total = 0
            for campaign, title in peer_campaigns:
                values = stat_map.get(
                    (placement.id, campaign.id),
                    {"delivery_count": 0, "valid_impressions": 0, "valid_clicks": 0},
                )
                deliveries = values["delivery_count"]
                delivery_total += deliveries
                impression_total += values["valid_impressions"]
                click_total += values["valid_clicks"]
                campaign_reports.append(
                    {
                        "campaign_id": campaign.id,
                        "title": title,
                        "delivery_count": deliveries,
                        "valid_impressions": values["valid_impressions"],
                        "valid_clicks": values["valid_clicks"],
                        "target_share_basis_points": (
                            weights[campaign.id] * 10_000 // total_weight
                            if total_weight
                            else 0
                        ),
                        "actual_share_basis_points": (
                            deliveries * 10_000 // total_deliveries
                            if total_deliveries
                            else 0
                        ),
                    }
                )
            paid_orders, revenue = order_map.get(placement.id, (0, 0))
            result.append(
                {
                    "placement_id": placement.id,
                    "placement_code": placement.code,
                    "placement_name": placement.name,
                    "paid_orders": paid_orders,
                    "paid_revenue_vnd": revenue,
                    "delivery_count": delivery_total,
                    "valid_impressions": impression_total,
                    "valid_clicks": click_total,
                    "ctr_basis_points": click_total * 10_000 // impression_total
                    if impression_total
                    else 0,
                    "campaigns": campaign_reports,
                }
            )
        return result

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        if "SUPER_ADMIN" not in principal.roles:
            raise AdvertisingForbiddenError()
