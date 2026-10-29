from datetime import UTC, datetime
from uuid import UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.auth.models import User
from app.modules.promotions.checkout_models import VoucherAdjustment, VoucherReservation
from app.modules.promotions.checkout_rules import discount_for, reject
from app.modules.promotions.models import VoucherCampaign, VoucherClaim
from app.modules.promotions.schemas import PromotionPolicy


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class PromotionCheckout:
    """Caller owns the transaction; no provider calls or hidden commits here.

    A HELD reservation is not released solely because its clock expires: provider
    outcomes must be reconciled first. This prevents late paid webhooks from
    consuming a voucher already handed to a second checkout.
    """

    def __init__(self, session: AsyncSession, *, now: datetime | None = None):
        self.session = session
        self.now = now or datetime.now(UTC)

    async def active(self, reference: str) -> VoucherReservation | None:
        return (
            await self.session.scalars(
                select(VoucherReservation).where(
                    VoucherReservation.order_reference == reference,
                    VoucherReservation.status.in_(["HELD", "REDEEMED"]),
                )
            )
        ).first()

    async def quote(
        self,
        user_id: UUID,
        service_code: str,
        original_vnd: int,
        *,
        product_id: str | None = None,
        membership_discount_vnd: int = 0,
    ) -> dict[str, object]:
        vouchers = []
        rows = list(
            await self.session.scalars(
                select(VoucherClaim)
                .where(
                    VoucherClaim.user_id == user_id, VoucherClaim.status == "AVAILABLE"
                )
                .order_by(VoucherClaim.expires_at, VoucherClaim.id)
            )
        )
        for claim in rows:
            try:
                campaign = await self.session.get(VoucherCampaign, claim.campaign_id)
                if campaign is None:
                    continue
                policy = await self._validate(claim, campaign, user_id, service_code)
                discount, payable = discount_for(
                    claim.amount_vnd,
                    policy.model_dump(mode="json", by_alias=False),
                    original_vnd=original_vnd,
                    service_code=service_code,
                    product_id=product_id,
                    membership_discount_vnd=membership_discount_vnd,
                )
                await self._limits(claim, campaign, policy, discount)
                vouchers.append(
                    {
                        "voucher_id": str(claim.id),
                        "title": claim.title,
                        "discount_vnd": discount,
                        "payable_vnd": payable,
                        "expires_at": claim.expires_at,
                    }
                )
            except DomainError:
                continue
        vouchers.sort(key=lambda item: int(str(item["discount_vnd"])), reverse=True)
        return {
            "original_vnd": original_vnd,
            "membership_discount_vnd": membership_discount_vnd,
            "vouchers": vouchers,
            "recommended_voucher_id": vouchers[0]["voucher_id"] if vouchers else None,
        }

    async def reserve(
        self,
        user_id: UUID,
        voucher_id: UUID,
        *,
        order_reference: str,
        service_code: str,
        original_vnd: int,
        expires_at: datetime,
        product_id: str | None = None,
        membership_discount_vnd: int = 0,
    ) -> VoucherReservation:
        await self.session.scalar(
            select(User.id).where(User.id == user_id).with_for_update()
        )
        replay = await self.active(order_reference)
        if replay is not None:
            if (
                replay.user_id != user_id
                or replay.voucher_id != voucher_id
                or replay.original_vnd != original_vnd
            ):
                reject(
                    "VOUCHER_CHECKOUT_CONFLICT",
                    "Checkout đã giữ một voucher hoặc giá khác.",
                )
            return replay
        ref = await self.session.get(VoucherClaim, voucher_id)
        if ref is None or ref.user_id != user_id:
            reject("VOUCHER_NOT_FOUND", "Voucher không thuộc tài khoản của bạn.")
        campaign = await self.session.scalar(
            select(VoucherCampaign)
            .where(VoucherCampaign.id == ref.campaign_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        claim = await self.session.scalar(
            select(VoucherClaim)
            .where(VoucherClaim.id == voucher_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert campaign is not None and claim is not None
        policy = await self._validate(claim, campaign, user_id, service_code)
        discount, payable = discount_for(
            claim.amount_vnd,
            policy.model_dump(mode="json", by_alias=False),
            original_vnd=original_vnd,
            service_code=service_code,
            product_id=product_id,
            membership_discount_vnd=membership_discount_vnd,
        )
        await self._limits(claim, campaign, policy, discount)
        if utc(expires_at) <= self.now:
            reject("VOUCHER_CHECKOUT_EXPIRED", "Checkout đã hết hạn.")
        row = VoucherReservation(
            voucher_id=claim.id,
            campaign_id=campaign.id,
            user_id=user_id,
            order_reference=order_reference,
            service_code=service_code,
            product_id=product_id,
            original_vnd=original_vnd,
            discount_vnd=discount,
            payable_vnd=payable,
            policy_version=claim.policy_version,
            snapshot_json=policy.model_dump(mode="json", by_alias=False),
            expires_at=expires_at,
            status="HELD",
            created_at=self.now,
        )
        self.session.add(row)
        claim.status = "RESERVED"
        campaign.budget_reserved_vnd += discount
        await self.session.flush()
        return row

    async def _validate(
        self,
        claim: VoucherClaim,
        campaign: VoucherCampaign,
        user_id: UUID,
        service_code: str,
    ) -> PromotionPolicy:
        from app.modules.promotions.audience import recipient_eligibility

        policy = PromotionPolicy.model_validate(
            claim.policy_json or campaign.policy_json
        )
        allowed, reason = await recipient_eligibility(self.session, user_id, policy)
        if not allowed:
            reject("VOUCHER_NOT_ELIGIBLE", reason)
        if claim.status != "AVAILABLE" or claim.uses_used >= policy.uses_per_voucher:
            reject(
                "VOUCHER_NOT_AVAILABLE", "Voucher đã được giữ, sử dụng hoặc thu hồi."
            )
        if utc(claim.expires_at) <= self.now or (
            claim.valid_from and utc(claim.valid_from) > self.now
        ):
            reject("VOUCHER_EXPIRED", "Voucher chưa có hoặc đã hết hiệu lực.")
        if campaign.status == "DRAFT":
            reject("VOUCHER_CAMPAIGN_INACTIVE", "Chiến dịch chưa được xuất bản.")
        if not policy.allow_use_after_end:
            if (
                campaign.status not in {"ACTIVE", "SCHEDULED"}
                or not campaign.active
                or (campaign.starts_at and utc(campaign.starts_at) > self.now)
                or (campaign.ends_at and utc(campaign.ends_at) <= self.now)
            ):
                reject("VOUCHER_CAMPAIGN_ENDED", "Chiến dịch đã ngừng áp dụng.")
        paid = await self._paid_orders(user_id, service_code)
        if policy.first_order_only and paid:
            reject("VOUCHER_FIRST_ORDER", "Voucher chỉ áp dụng giao dịch đầu tiên.")
        if policy.first_order_only:
            held = await self.session.scalar(
                select(VoucherReservation.id)
                .where(
                    VoucherReservation.user_id == user_id,
                    VoucherReservation.service_code == service_code,
                    VoucherReservation.status == "HELD",
                )
                .limit(1)
            )
            if held is not None:
                reject(
                    "VOUCHER_FIRST_ORDER_HELD", "Giao dịch đầu tiên đang được xử lý."
                )
        if policy.subsequent_order_only and not paid:
            reject("VOUCHER_SUBSEQUENT_ORDER", "Voucher dành cho giao dịch tiếp theo.")
        return policy

    async def _paid_orders(self, user_id: UUID, service_code: str) -> int:
        from app.modules.advertising.models import AdvertisingOrder
        from app.modules.memberships.models import MembershipPurchase
        from app.modules.payments.models import PaymentOrder, PaymentStatus

        if service_code == "MEMBERSHIP":
            query = (
                select(func.count())
                .select_from(MembershipPurchase)
                .where(MembershipPurchase.user_id == user_id)
            )
        elif service_code == "ADVERTISING":
            query = (
                select(func.count())
                .select_from(AdvertisingOrder)
                .where(
                    AdvertisingOrder.user_id == user_id,
                    AdvertisingOrder.payment_status == "PAID",
                )
            )
        else:
            query = (
                select(func.count())
                .select_from(PaymentOrder)
                .where(
                    PaymentOrder.initiated_by_user_id == user_id,
                    PaymentOrder.status == PaymentStatus.PAID,
                )
            )
        return int(await self.session.scalar(query) or 0)

    async def _limits(
        self,
        claim: VoucherClaim,
        campaign: VoucherCampaign,
        policy: PromotionPolicy,
        discount: int,
    ) -> None:
        current = PromotionPolicy.model_validate(campaign.policy_json)
        budget = current.budget_vnd
        if (
            budget is not None
            and campaign.budget_reserved_vnd + campaign.budget_spent_vnd + discount
            > budget
        ):
            reject(
                "VOUCHER_BUDGET_EXHAUSTED",
                "Ngân sách ưu đãi đã được sử dụng hoặc đang giữ.",
            )
        base = (
            select(func.count())
            .select_from(VoucherReservation)
            .where(
                VoucherReservation.campaign_id == campaign.id,
                VoucherReservation.status.in_(["HELD", "REDEEMED"]),
            )
        )
        if (
            policy.redemption_limit is not None
            and int(await self.session.scalar(base) or 0) >= policy.redemption_limit
        ):
            reject("VOUCHER_USAGE_LIMIT", "Chiến dịch đã đạt giới hạn sử dụng.")
        if policy.daily_limit is not None:
            today = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
            if (
                int(
                    await self.session.scalar(
                        base.where(VoucherReservation.created_at >= today)
                    )
                    or 0
                )
                >= policy.daily_limit
            ):
                reject("VOUCHER_DAILY_LIMIT", "Chiến dịch đã đạt giới hạn trong ngày.")
        if policy.user_discount_limit_vnd is not None:
            used = await self.session.scalar(
                select(
                    func.coalesce(func.sum(VoucherReservation.discount_vnd), 0)
                ).where(
                    VoucherReservation.user_id == claim.user_id,
                    VoucherReservation.campaign_id == campaign.id,
                    VoucherReservation.status.in_(["HELD", "REDEEMED"]),
                )
            )
            if int(used or 0) + discount > policy.user_discount_limit_vnd:
                reject(
                    "VOUCHER_USER_LIMIT",
                    "Tài khoản đã đạt giới hạn ưu đãi của chiến dịch.",
                )

    async def _locked(
        self, reference: str
    ) -> tuple[VoucherReservation, VoucherCampaign, VoucherClaim] | None:
        ref = await self.active(reference)
        if ref is None:
            return None
        await self.session.scalar(
            select(User.id).where(User.id == ref.user_id).with_for_update()
        )
        campaign = await self.session.scalar(
            select(VoucherCampaign)
            .where(VoucherCampaign.id == ref.campaign_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        claim = await self.session.scalar(
            select(VoucherClaim)
            .where(VoucherClaim.id == ref.voucher_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = await self.session.scalar(
            select(VoucherReservation)
            .where(VoucherReservation.id == ref.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert row is not None and campaign is not None and claim is not None
        return row, campaign, claim

    async def redeem(self, reference: str) -> None:
        locked = await self._locked(reference)
        if locked is None:
            return
        row, campaign, claim = locked
        if row.status == "REDEEMED":
            return
        if row.status != "HELD":
            reject(
                "VOUCHER_RESERVATION_INVALID", "Không tìm thấy lượt giữ voucher hợp lệ."
            )
        row.status, row.redeemed_at = "REDEEMED", self.now
        campaign.budget_reserved_vnd -= row.discount_vnd
        campaign.budget_spent_vnd += row.discount_vnd
        claim.uses_used += 1
        claim.redeemed_at = self.now
        policy = PromotionPolicy.model_validate(row.snapshot_json)
        claim.status = (
            "REDEEMED" if claim.uses_used >= policy.uses_per_voucher else "AVAILABLE"
        )
        from app.modules.notifications.models import Notification

        self.session.add(
            Notification(
                user_id=row.user_id,
                source_event_id=uuid5(row.id, "redeemed"),
                type="VOUCHER_REDEEMED",
                title="Bạn đã sử dụng ưu đãi",
                body=f"Bạn đã tiết kiệm {row.discount_vnd:,}đ.",
                data_json={"actionPath": "/vouchers"},
                created_at=self.now,
            )
        )
        await self.session.flush()

    async def release(
        self, reference: str, *, reason: str, definitive: bool = True
    ) -> None:
        if not definitive:
            return
        locked = await self._locked(reference)
        if locked is None:
            return
        row, campaign, claim = locked
        if row.status != "HELD":
            return
        row.status = "RELEASED"
        campaign.budget_reserved_vnd -= row.discount_vnd
        claim.status = "AVAILABLE"
        self.session.add(
            VoucherAdjustment(
                reservation_id=row.id,
                reference=f"release:{row.id}",
                kind="RELEASE",
                discount_vnd=0,
                refund_vnd=0,
                reason=reason,
            )
        )
        await self.session.flush()

    async def refund(
        self,
        reference: str,
        *,
        refund_reference: str,
        refund_vnd: int | None = None,
        reason: str = "Hoàn tiền đã được xác nhận",
    ) -> None:
        locked = await self._locked(reference)
        if locked is None:
            return
        row, campaign, claim = locked
        existing = await self.session.scalar(
            select(VoucherAdjustment.id).where(
                VoucherAdjustment.reference == refund_reference
            )
        )
        if existing is not None:
            return
        if row.status != "REDEEMED":
            reject("VOUCHER_REFUND_INVALID", "Voucher chưa được sử dụng thành công.")
        refunded = int(
            await self.session.scalar(
                select(func.coalesce(func.sum(VoucherAdjustment.refund_vnd), 0)).where(
                    VoucherAdjustment.reservation_id == row.id,
                    VoucherAdjustment.kind == "REFUND",
                )
            )
            or 0
        )
        amount = row.payable_vnd - refunded if refund_vnd is None else refund_vnd
        if type(amount) is not int or amount < 0 or refunded + amount > row.payable_vnd:
            reject("VOUCHER_REFUND_AMOUNT", "Số tiền hoàn không hợp lệ.")
        reversed_so_far = int(
            await self.session.scalar(
                select(
                    func.coalesce(func.sum(VoucherAdjustment.discount_vnd), 0)
                ).where(
                    VoucherAdjustment.reservation_id == row.id,
                    VoucherAdjustment.kind == "REFUND",
                )
            )
            or 0
        )
        full = refunded + amount == row.payable_vnd
        reversal = (
            row.discount_vnd - reversed_so_far
            if full
            else row.discount_vnd * amount // max(row.payable_vnd, 1)
        )
        campaign.budget_spent_vnd -= reversal
        policy = PromotionPolicy.model_validate(row.snapshot_json)
        if full and policy.restore_on_refund and utc(claim.expires_at) > self.now:
            claim.uses_used = max(0, claim.uses_used - 1)
            claim.status = "AVAILABLE"
        self.session.add(
            VoucherAdjustment(
                reservation_id=row.id,
                reference=refund_reference,
                kind="REFUND",
                discount_vnd=reversal,
                refund_vnd=amount,
                reason=reason,
            )
        )
        await self.session.flush()
