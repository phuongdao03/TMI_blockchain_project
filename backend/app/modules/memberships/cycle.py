from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memberships.models import (
    MembershipPlan,
    MembershipPurchase,
    UserMembership,
)


def _utc(value: datetime) -> datetime:
    normalized = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return normalized.astimezone(UTC)


async def active_membership_cycle(
    session: AsyncSession, user_id: UUID
) -> tuple[str, datetime | None]:
    membership = await session.get(UserMembership, user_id)
    now = datetime.now(UTC)
    if membership is None or _utc(membership.expires_at) <= now:
        return "MEMBER", None

    purchases = await session.execute(
        select(MembershipPurchase.expires_at, MembershipPlan.duration_days)
        .join(MembershipPlan, MembershipPlan.id == MembershipPurchase.plan_id)
        .where(
            MembershipPurchase.user_id == user_id,
            MembershipPurchase.tier == membership.tier,
            MembershipPurchase.expires_at <= membership.expires_at,
        )
        .order_by(MembershipPurchase.expires_at.desc())
    )
    cycle_durations = {
        _utc(expiry): duration_days for expiry, duration_days in purchases.all()
    }
    cycle_end = _utc(membership.expires_at)
    while cycle_end in cycle_durations:
        cycle_start = cycle_end - timedelta(days=cycle_durations[cycle_end])
        if cycle_start <= now:
            return membership.tier, cycle_start
        cycle_end = cycle_start

    plan = await session.get(MembershipPlan, membership.plan_id)
    duration_days = plan.duration_days if plan is not None else 365
    return membership.tier, _utc(membership.expires_at) - timedelta(
        days=duration_days
    )
