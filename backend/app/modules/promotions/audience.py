from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserPermission,
    UserRole,
    UserStatus,
)
from app.modules.hr.models import Employee
from app.modules.memberships.models import MembershipPurchase, UserMembership
from app.modules.payments.models import PaymentOrder, PaymentStatus
from app.modules.promotions.schemas import PromotionPolicy


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def purchase_count(session: AsyncSession, user_id: UUID) -> int:
    payments = await session.scalar(
        select(func.count())
        .select_from(PaymentOrder)
        .where(
            PaymentOrder.initiated_by_user_id == user_id,
            PaymentOrder.status == PaymentStatus.PAID,
        )
    )
    memberships = await session.scalar(
        select(func.count())
        .select_from(MembershipPurchase)
        .where(MembershipPurchase.user_id == user_id)
    )
    # Advertising purchases are recorded in their existing order table.
    from app.modules.advertising.models import AdvertisingOrder

    advertising = await session.scalar(
        select(func.count())
        .select_from(AdvertisingOrder)
        .where(
            AdvertisingOrder.user_id == user_id,
            AdvertisingOrder.payment_status == "PAID",
        )
    )
    return int(payments or 0) + int(memberships or 0) + int(advertising or 0)


async def recipient_eligibility(
    session: AsyncSession, user_id: UUID, policy: PromotionPolicy
) -> tuple[bool, str]:
    user = await session.get(User, user_id)
    if (
        user is None
        or user.status != UserStatus.ACTIVE
        or user.disabled_at
        or user.deleted_at
    ):
        return False, "ACCOUNT_INACTIVE"
    roles = set(
        await session.scalars(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
    )
    if roles != {"USER"}:
        return False, "INTERNAL_OR_NON_USER"
    internal = {
        "promotions.manage",
        "promotions.read",
        "users.read",
        "staff.read",
        "review.assign",
        "work.allocations.manage",
        "payments.read",
        "memberships.manage",
        "audit.read",
        "reports.read",
        "public_content.manage",
        "community.manage",
        "community.moderate",
        "dashboard.read",
    }
    direct = await session.scalars(
        select(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(
            UserPermission.user_id == user_id,
            or_(
                UserPermission.expires_at.is_(None),
                UserPermission.expires_at > datetime.now(UTC),
            ),
        )
    )
    inherited = await session.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    if any(
        code in internal or code.startswith("hr.") for code in [*direct, *inherited]
    ):
        return False, "INTERNAL_PERMISSION"
    if await session.scalar(
        select(Employee.id).where(Employee.user_id == user_id).limit(1)
    ):
        return False, "EMPLOYEE"
    rule = policy.audience
    checks: list[tuple[bool, str]] = []
    if rule.registered_before:
        checks.append(
            (utc(user.created_at) < rule.registered_before, "REGISTERED_TOO_LATE")
        )
    if rule.registered_after:
        checks.append(
            (utc(user.created_at) >= rule.registered_after, "REGISTERED_TOO_EARLY")
        )
    if rule.user_ids:
        checks.append((user_id in rule.user_ids, "NOT_SELECTED"))
    if rule.membership_tiers:
        membership = await session.get(UserMembership, user_id)
        tier = (
            membership.tier
            if membership and utc(membership.expires_at) > datetime.now(UTC)
            else "MEMBER"
        )
        checks.append((tier in rule.membership_tiers, "MEMBERSHIP_TIER"))
    if rule.purchase_history != "ANY":
        count = await purchase_count(session, user_id)
        checks.append(
            (
                (count == 0 if rule.purchase_history == "FIRST" else count > 0),
                "PURCHASE_HISTORY",
            )
        )
    if not checks:
        return True, "ELIGIBLE"
    eligible = (
        all(item[0] for item in checks)
        if rule.mode == "ALL"
        else any(item[0] for item in checks)
    )
    return eligible, "ELIGIBLE" if eligible else next(
        reason for passed, reason in checks if not passed
    )
