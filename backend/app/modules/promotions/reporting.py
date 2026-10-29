from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.promotions.checkout_models import VoucherAdjustment, VoucherReservation
from app.modules.promotions.models import (
    VoucherCampaign,
    VoucherClaim,
    VoucherPresentationState,
)
from app.modules.promotions.schemas import PromotionPolicy


async def analytics(
    session: AsyncSession,
    campaign_id: UUID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    service_code: str | None = None,
    status: str | None = None,
    *,
    transaction_limit: int | None = 100,
    transaction_offset: int = 0,
) -> dict[str, object]:
    campaigns = list(
        await session.scalars(
            select(VoucherCampaign).where(
                *([VoucherCampaign.id == campaign_id] if campaign_id else [])
            )
        )
    )
    ids = [row.id for row in campaigns]
    claim_filters: list[ColumnElement[bool]] = [VoucherClaim.campaign_id.in_(ids)]
    order_filters: list[ColumnElement[bool]] = [VoucherReservation.campaign_id.in_(ids)]
    if start:
        claim_filters.append(VoucherClaim.claimed_at >= start)
        order_filters.append(VoucherReservation.created_at >= start)
    if end:
        claim_filters.append(VoucherClaim.claimed_at < end)
        order_filters.append(VoucherReservation.created_at < end)
    if service_code:
        order_filters.append(VoucherReservation.service_code == service_code)
    if status:
        claim_filters.append(VoucherClaim.status == status)
    now = datetime.now(UTC)
    issued, nominal, available, expired, redeemed = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(VoucherClaim.amount_vnd), 0),
                func.count().filter(
                    VoucherClaim.status == "AVAILABLE", VoucherClaim.expires_at > now
                ),
                func.count().filter(
                    VoucherClaim.expires_at <= now, VoucherClaim.status == "AVAILABLE"
                ),
                func.count().filter(VoucherClaim.status == "REDEEMED"),
            ).where(*claim_filters)
        )
    ).one()
    spent, reserved, revenue, redemption_count = (
        await session.execute(
            select(
                func.coalesce(
                    func.sum(VoucherReservation.discount_vnd).filter(
                        VoucherReservation.status == "REDEEMED"
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(VoucherReservation.discount_vnd).filter(
                        VoucherReservation.status == "HELD"
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(VoucherReservation.payable_vnd).filter(
                        VoucherReservation.status == "REDEEMED"
                    ),
                    0,
                ),
                func.count().filter(VoucherReservation.status == "REDEEMED"),
            ).where(*order_filters)
        )
    ).one()
    refund_discount, refunded_revenue = (
        await session.execute(
            select(
                func.coalesce(func.sum(VoucherAdjustment.discount_vnd), 0),
                func.coalesce(func.sum(VoucherAdjustment.refund_vnd), 0),
            )
            .join(
                VoucherReservation,
                VoucherReservation.id == VoucherAdjustment.reservation_id,
            )
            .where(*order_filters, VoucherAdjustment.kind == "REFUND")
        )
    ).one()
    views, clicks = (
        await session.execute(
            select(
                func.coalesce(func.sum(VoucherPresentationState.seen_count), 0),
                func.count().filter(VoucherPresentationState.clicked_at.is_not(None)),
            ).where(VoucherPresentationState.campaign_id.in_(ids))
        )
    ).one()
    issuance_days = (
        await session.execute(
            select(func.date(VoucherClaim.claimed_at), func.count())
            .where(*claim_filters)
            .group_by(func.date(VoucherClaim.claimed_at))
        )
    ).all()
    redemption_days = (
        await session.execute(
            select(func.date(VoucherReservation.redeemed_at), func.count())
            .where(*order_filters, VoucherReservation.status == "REDEEMED")
            .group_by(func.date(VoucherReservation.redeemed_at))
        )
    ).all()
    daily: dict[str, dict[str, object]] = {}
    for day, count in issuance_days:
        daily[str(day)] = {"date": str(day), "issued": count, "redeemed": 0}
    for day, count in redemption_days:
        daily.setdefault(str(day), {"date": str(day), "issued": 0, "redeemed": 0})[
            "redeemed"
        ] = count
    budgets = [
        PromotionPolicy.model_validate(row.policy_json).budget_vnd for row in campaigns
    ]
    budget = (
        sum(value for value in budgets if value is not None)
        if any(value is not None for value in budgets)
        else None
    )
    transaction_query = (
        select(VoucherReservation)
        .where(*order_filters)
        .order_by(VoucherReservation.created_at.desc(), VoucherReservation.id)
        .offset(transaction_offset)
    )
    if transaction_limit is not None:
        transaction_query = transaction_query.limit(transaction_limit)
    transactions = list(await session.scalars(transaction_query))
    transaction_count = await session.scalar(
        select(func.count()).select_from(VoucherReservation).where(*order_filters)
    )
    return {
        "campaignCount": len(campaigns),
        "activeCampaignCount": sum(
            row.active
            and row.status in {"ACTIVE", "SCHEDULED"}
            and (not row.ends_at or row.ends_at.replace(tzinfo=UTC) > now)
            for row in campaigns
        ),
        "issuedCount": issued,
        "availableCount": available,
        "redeemedCount": redeemed,
        "redemptionCount": redemption_count,
        "expiredCount": expired,
        "issuedValueVnd": nominal,
        "reservedVnd": reserved,
        "discountVnd": max(0, spent - refund_discount),
        "revenueVnd": max(0, revenue - refunded_revenue),
        "budgetRemainingVnd": max(
            0,
            budget
            - sum(row.budget_spent_vnd + row.budget_reserved_vnd for row in campaigns),
        )
        if budget is not None
        else None,
        "viewCount": views,
        "clickCount": clicks,
        "redemptionRate": redeemed / issued if issued else 0,
        "budgetWarningPercent": int(
            (
                sum(row.budget_spent_vnd + row.budget_reserved_vnd for row in campaigns)
                * 100
            )
            // budget
        )
        if budget
        else 0,
        "daily": [daily[key] for key in sorted(daily)],
        "transactionCount": transaction_count or 0,
        "transactions": [
            {
                "id": str(row.id),
                "orderReference": row.order_reference,
                "orderId": row.order_reference,
                "campaignId": str(row.campaign_id),
                "voucherId": str(row.voucher_id),
                "serviceCode": row.service_code,
                "status": row.status,
                "originalVnd": row.original_vnd,
                "discountVnd": row.discount_vnd,
                "payableVnd": row.payable_vnd,
                "revenueVnd": row.payable_vnd if row.status == "REDEEMED" else 0,
                "createdAt": row.created_at.isoformat(),
                "redeemedAt": row.redeemed_at.isoformat() if row.redeemed_at else None,
            }
            for row in transactions
        ],
    }
