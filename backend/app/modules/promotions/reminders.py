from datetime import UTC, datetime, timedelta
from uuid import uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification
from app.modules.promotions.audience import recipient_eligibility
from app.modules.promotions.distribution_models import PromotionExpiryReminder
from app.modules.promotions.models import VoucherClaim
from app.modules.promotions.schemas import PromotionPolicy


async def notify_expiring_vouchers(
    session: AsyncSession, *, now: datetime | None = None, limit: int = 500
) -> int:
    now = now or datetime.now(UTC)
    already_notified = (
        select(PromotionExpiryReminder.voucher_id)
        .where(PromotionExpiryReminder.voucher_id == VoucherClaim.id)
        .exists()
    )
    claims = list(
        await session.scalars(
            select(VoucherClaim)
            .where(
                VoucherClaim.status == "AVAILABLE",
                VoucherClaim.expires_at > now,
                VoucherClaim.expires_at <= now + timedelta(days=3),
                ~already_notified,
            )
            .order_by(VoucherClaim.expires_at, VoucherClaim.id)
            .limit(min(max(limit, 1), 1000))
            .with_for_update(skip_locked=True)
        )
    )
    sent = 0
    for claim in claims:
        policy = PromotionPolicy.model_validate(claim.policy_json or {})
        if not policy.presentation.notify_in_app:
            continue
        eligible, _ = await recipient_eligibility(session, claim.user_id, policy)
        if not eligible:
            continue
        session.add(
            Notification(
                user_id=claim.user_id,
                source_event_id=uuid5(claim.id, "expiring"),
                type="voucher.expiring",
                title="Voucher của bạn sắp hết hạn",
                body=(
                    "Ưu đãi của bạn sẽ hết hạn trong ba ngày tới. Xem "
                    "điều kiện và sử dụng trước hạn."
                ),
                data_json={
                    "voucherId": str(claim.id),
                    "actionPath": f"/vouchers/{claim.id}",
                },
                created_at=now,
            )
        )
        session.add(PromotionExpiryReminder(voucher_id=claim.id, notified_at=now))
        sent += 1
    await session.commit()
    return sent
