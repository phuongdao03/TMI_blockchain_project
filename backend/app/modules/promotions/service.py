from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4, uuid5

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import DomainError
from app.modules.auth.models import User
from app.modules.notifications.models import Notification
from app.modules.promotions.audience import recipient_eligibility, utc
from app.modules.promotions.models import (
    VoucherCampaign,
    VoucherClaim,
    VoucherPresentationState,
)
from app.modules.promotions.schemas import PromotionPolicy


def _availability(now: datetime) -> tuple[ColumnElement[bool], ...]:
    return (
        VoucherCampaign.active.is_(True),
        VoucherCampaign.status.in_(("ACTIVE", "SCHEDULED")),
        or_(VoucherCampaign.starts_at.is_(None), VoucherCampaign.starts_at <= now),
        or_(VoucherCampaign.ends_at.is_(None), VoucherCampaign.ends_at > now),
    )


def _error(code: str, message: str) -> DomainError:
    return DomainError(code=code, message=message, status_code=409)


class VoucherService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def offer(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
        session_id: UUID | None = None,
        trigger: str = "LOGIN",
    ) -> VoucherCampaign | None:
        now = now or datetime.now(UTC)
        campaigns = await self.session.scalars(
            select(VoucherCampaign)
            .where(*_availability(now))
            .order_by(VoucherCampaign.code)
        )
        for row in campaigns:
            policy = PromotionPolicy.model_validate(row.policy_json)
            if row.program_type in {"MANUAL", "CODE"}:
                continue
            if not (await recipient_eligibility(self.session, user_id, policy))[0]:
                continue
            voucher = await self.session.scalar(
                select(VoucherClaim).where(
                    VoucherClaim.user_id == user_id, VoucherClaim.campaign_id == row.id
                )
            )
            if row.program_type in {"AUTO", "FIRST_ORDER"} and voucher is None:
                try:
                    async with self.session.begin_nested():
                        voucher = await self.issue(
                            user_id, row.id, reason="automatic", now=now, commit=False
                        )
                        for slot in range(2, policy.vouchers_per_user + 1):
                            await self.issue(
                                user_id,
                                row.id,
                                reason="automatic",
                                now=now,
                                commit=False,
                                issuance_slot=slot,
                            )
                except DomainError:
                    continue
            elif voucher is not None and row.program_type == "CLAIM":
                continue
            if voucher and (
                voucher.status in {"REDEEMED", "REVOKED"}
                or utc(voucher.expires_at) <= now
            ):
                continue
            display = policy.presentation
            allowed_triggers = {trigger, "ISSUED"}
            if trigger == "DASHBOARD":
                allowed_triggers.add("LOGIN")
            if not display.enabled or display.trigger not in allowed_triggers:
                continue
            state = await self.session.get(VoucherPresentationState, (user_id, row.id))
            if state:
                if state.opt_out or (
                    display.frequency == "ONCE"
                    and (state.seen_count > 0 or state.dismissed_at)
                ):
                    continue
                if (
                    display.frequency == "SESSION"
                    and session_id
                    and state.last_session_id == session_id
                ):
                    continue
                if (
                    display.frequency == "LIMITED"
                    and state.seen_count >= display.max_views
                ):
                    continue
                if state.last_seen_at and now - utc(state.last_seen_at) < timedelta(
                    hours=display.cooldown_hours
                ):
                    continue
            await self.session.commit()
            await self.session.refresh(row)
            return row
        await self.session.commit()
        return None

    async def mine(self, user_id: UUID) -> list[VoucherClaim]:
        return list(
            await self.session.scalars(
                select(VoucherClaim)
                .where(VoucherClaim.user_id == user_id)
                .order_by(VoucherClaim.claimed_at.desc(), VoucherClaim.id)
            )
        )

    async def claim(
        self, user_id: UUID, campaign_id: UUID, *, now: datetime | None = None
    ) -> VoucherClaim:
        campaign = await self.session.get(VoucherCampaign, campaign_id)
        if campaign and campaign.program_type in {"MANUAL", "CODE"}:
            raise _error(
                "VOUCHER_CODE_REQUIRED", "Hãy nhập mã voucher hoặc chờ được cấp ưu đãi."
            )
        first = await self.issue(user_id, campaign_id, now=now, commit=False)
        if campaign is not None:
            policy = PromotionPolicy.model_validate(campaign.policy_json)
            for slot in range(2, policy.vouchers_per_user + 1):
                await self.issue(
                    user_id, campaign_id, now=now, commit=False, issuance_slot=slot
                )
        await self.session.commit()
        await self.session.refresh(first)
        return first

    async def issue(
        self,
        user_id: UUID,
        campaign_id: UUID,
        *,
        reason: str = "claim",
        commit: bool = True,
        now: datetime | None = None,
        issuance_slot: int = 1,
    ) -> VoucherClaim:
        now = now or datetime.now(UTC)
        await self.session.scalar(
            select(User.id).where(User.id == user_id).with_for_update()
        )
        campaign = await self.session.scalar(
            select(VoucherCampaign)
            .where(VoucherCampaign.id == campaign_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if campaign is None:
            raise _error("VOUCHER_UNAVAILABLE", "Ưu đãi không còn khả dụng.")
        policy = PromotionPolicy.model_validate(campaign.policy_json)
        if reason == "claim" and campaign.program_type in {"MANUAL", "CODE"}:
            raise _error(
                "VOUCHER_CODE_REQUIRED", "Hãy nhập mã hoặc chờ được cấp ưu đãi."
            )
        if not 1 <= issuance_slot <= policy.vouchers_per_user:
            raise _error(
                "VOUCHER_LIMIT_REACHED", "Tài khoản đã đạt giới hạn nhận voucher."
            )
        eligible, why = await recipient_eligibility(self.session, user_id, policy)
        if not eligible:
            raise DomainError(
                code="VOUCHER_NOT_ELIGIBLE",
                message="Tài khoản không thuộc đối tượng nhận voucher.",
                status_code=403,
                details={"reason": why},
            )
        query = select(VoucherClaim).where(
            VoucherClaim.user_id == user_id,
            VoucherClaim.campaign_id == campaign_id,
            VoucherClaim.issuance_slot == issuance_slot,
        )
        existing = await self.session.scalar(query)
        if existing:
            if commit:
                await self.session.commit()
                await self.session.refresh(existing)
            return existing
        available = campaign.active and campaign.status in {"ACTIVE", "SCHEDULED"}
        available = (
            available
            and (not campaign.starts_at or utc(campaign.starts_at) <= now)
            and (not campaign.ends_at or utc(campaign.ends_at) > now)
        )
        if not available:
            raise _error("VOUCHER_UNAVAILABLE", "Ưu đãi không còn khả dụng.")
        count = int(
            await self.session.scalar(
                select(func.count())
                .select_from(VoucherClaim)
                .where(VoucherClaim.campaign_id == campaign_id)
            )
            or 0
        )
        if policy.issuance_limit is not None and count >= policy.issuance_limit:
            raise _error(
                "VOUCHER_LIMIT_REACHED", "Chiến dịch đã phát hết số lượng voucher."
            )
        expiry = policy.fixed_expires_at or now + timedelta(days=campaign.validity_days)
        if expiry <= now:
            raise _error("VOUCHER_UNAVAILABLE", "Voucher đã hết hạn.")
        row = VoucherClaim(
            id=uuid4(),
            user_id=user_id,
            campaign_id=campaign_id,
            title=campaign.title,
            terms=campaign.terms,
            image_path=campaign.image_path,
            amount_vnd=campaign.amount_vnd,
            claimed_at=now,
            expires_at=expiry,
            valid_from=now,
            policy_json=policy.model_dump(mode="json", by_alias=False),
            policy_version=campaign.policy_version,
            status="AVAILABLE",
            unique_code=f"THV-{uuid4().hex[:16].upper()}",
            issue_reason=reason[:255],
            issuance_slot=issuance_slot,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
                if policy.presentation.notify_in_app:
                    self.session.add(
                        Notification(
                            user_id=user_id,
                            source_event_id=uuid5(row.id, "issued"),
                            type="voucher.issued",
                            title="Bạn vừa nhận được ưu đãi",
                            body=(
                                f"{campaign.title}. Xem điều kiện và hạn "
                                "dùng trong kho voucher."
                            ),
                            data_json={"actionPath": f"/vouchers/{row.id}"},
                            created_at=now,
                        )
                    )
                    await self.session.flush()
        except IntegrityError:
            existing = await self.session.scalar(query)
            if existing is None:
                raise
            row = existing
        if commit:
            await self.session.commit()
            await self.session.refresh(row)
        return row

    async def presentation_event(
        self, user_id: UUID, campaign_id: UUID, session_id: UUID, event: str
    ) -> None:
        await self.session.scalar(
            select(User.id).where(User.id == user_id).with_for_update()
        )
        campaign = await self.session.get(VoucherCampaign, campaign_id)
        if (
            not campaign
            or not (
                await recipient_eligibility(
                    self.session,
                    user_id,
                    PromotionPolicy.model_validate(campaign.policy_json),
                )
            )[0]
        ):
            raise DomainError(
                code="VOUCHER_NOT_ELIGIBLE",
                message="Ưu đãi không khả dụng.",
                status_code=403,
            )
        state = await self.session.get(VoucherPresentationState, (user_id, campaign_id))
        if state is None:
            state = VoucherPresentationState(
                user_id=user_id, campaign_id=campaign_id, seen_count=0
            )
            self.session.add(state)
        now = datetime.now(UTC)
        if event == "SEEN" and state.last_session_id != session_id:
            state.seen_count += 1
            state.last_seen_at = now
        elif event == "CLICKED":
            state.clicked_at = now
        elif event == "DISMISSED":
            state.dismissed_at = now
        elif event == "OPT_OUT":
            state.opt_out = True
            state.dismissed_at = now
        state.last_session_id = session_id
        await self.session.commit()
