import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.affiliate.models import (
    AffiliateAttribution,
    AffiliateCommission,
    AffiliateCommissionRate,
    AffiliateCommissionRuleSet,
    AffiliateProfile,
    AffiliateReferralClick,
)
from app.modules.audit.models import AuditActorType, AuditLog
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.hr.models import Employee
from app.modules.notifications.models import Notification
from app.modules.wallet.models import FinanceAccount, FinanceEntry, FinanceJournal
from app.modules.wallet.service import FinanceLedger


@dataclass(frozen=True, slots=True)
class AffiliateDashboard:
    profile: AffiliateProfile
    click_count: int
    attributed_user_count: int
    pending_commission_minor: int
    on_hold_commission_minor: int
    available_balance_minor: int
    reserved_balance_minor: int
    lifetime_earned_minor: int
    total_withdrawn_minor: int
    total_reversed_minor: int


@dataclass(frozen=True, slots=True)
class AffiliateReferralSummary:
    id: UUID
    attributed_at: datetime
    expires_at: datetime
    conversion_count: int
    revenue_minor: int
    commission_amount_minor: int


@dataclass(frozen=True, slots=True)
class AffiliateProfileAdminSummary:
    user_id: UUID
    referral_code: str
    status: str
    created_at: datetime
    click_count: int
    attributed_user_count: int


@dataclass(frozen=True, slots=True)
class CommissionRuleSetView:
    rule_set: AffiliateCommissionRuleSet
    rates: tuple[AffiliateCommissionRate, ...]


class AffiliateService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        affiliate_enabled: bool = False,
        direct_commission_enabled: bool = False,
        clock=None,
        code_factory=None,
    ) -> None:
        self.session = session
        self.affiliate_enabled = affiliate_enabled
        self.direct_commission_enabled = direct_commission_enabled
        self._clock = clock or (lambda: datetime.now(UTC))
        self._code_factory = code_factory or (
            lambda: f"THV{secrets.token_hex(6).upper()}"
        )

    async def dashboard(self, user_id: UUID) -> AffiliateDashboard:
        async with self.session.begin():
            profile = await self.ensure_profile_in_current_transaction(
                user_id, allow_pending=False
            )
            clicks = await self.session.scalar(
                select(func.count())
                .select_from(AffiliateReferralClick)
                .where(AffiliateReferralClick.affiliate_user_id == user_id)
            )
            referrals = await self.session.scalar(
                select(func.count())
                .select_from(AffiliateAttribution)
                .where(AffiliateAttribution.affiliate_user_id == user_id)
            )
            pending = await self._commission_total(user_id, "PENDING")
            on_hold = await self._commission_total(user_id, "ON_HOLD")
            earned = await self.session.scalar(
                select(
                    func.coalesce(
                        func.sum(AffiliateCommission.commission_amount_minor), 0
                    )
                ).where(
                    AffiliateCommission.affiliate_user_id == user_id,
                    AffiliateCommission.status.in_(
                        ("PENDING", "ON_HOLD", "AVAILABLE", "REVERSED")
                    ),
                )
            )
            reversed_total = await self._commission_total(user_id, "REVERSED")
            ledger = FinanceLedger(self.session)
            available_account, reserved_account = await ledger.user_accounts(user_id)
            available_balance = await ledger.balance(available_account.id)
            reserved_balance = await ledger.balance(reserved_account.id)
            withdrawn = await self.session.scalar(
                select(
                    func.coalesce(func.sum(-FinanceEntry.amount_minor), 0)
                )
                .join(FinanceJournal, FinanceJournal.id == FinanceEntry.journal_id)
                .join(
                    FinanceAccount,
                    FinanceAccount.id == FinanceEntry.account_id,
                )
                .where(
                    FinanceAccount.owner_user_id == user_id,
                    FinanceAccount.account_type == "COMMISSION_RESERVED",
                    FinanceJournal.transaction_type == "PAYOUT_SETTLEMENT",
                    FinanceEntry.amount_minor < 0,
                )
            )
            return AffiliateDashboard(
                profile=profile,
                click_count=int(clicks or 0),
                attributed_user_count=int(referrals or 0),
                pending_commission_minor=pending,
                on_hold_commission_minor=on_hold,
                available_balance_minor=available_balance,
                reserved_balance_minor=reserved_balance,
                lifetime_earned_minor=int(earned or 0),
                total_withdrawn_minor=int(withdrawn or 0),
                total_reversed_minor=reversed_total,
            )

    async def ensure_profile(self, user_id: UUID) -> AffiliateProfile:
        async with self.session.begin():
            return await self.ensure_profile_in_current_transaction(
                user_id, allow_pending=False
            )

    async def ensure_profile_in_current_transaction(
        self, user_id: UUID, *, allow_pending: bool = True
    ) -> AffiliateProfile:
        await self._require_eligible_user(user_id, allow_pending=allow_pending)
        profile = await self.session.get(AffiliateProfile, user_id)
        if profile is not None:
            if profile.status != "ACTIVE":
                raise _forbidden()
            return profile

        for _ in range(3):
            profile = AffiliateProfile(
                user_id=user_id,
                referral_code=self._code_factory(),
                status="ACTIVE",
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(profile)
                    await self.session.flush()
            except IntegrityError as exc:
                existing = await self.session.get(AffiliateProfile, user_id)
                if existing is not None:
                    if existing.status != "ACTIVE":
                        raise _forbidden() from exc
                    return existing
                continue
            return profile
        raise DomainError(
            code="AFFILIATE_PROFILE_UNAVAILABLE",
            message="Không thể tạo hồ sơ giới thiệu lúc này.",
            status_code=503,
        )

    async def capture_signup_referral_in_current_transaction(
        self,
        *,
        referred_user_id: UUID,
        referral_code: str,
        click_id: UUID | None = None,
    ) -> AffiliateAttribution | None:
        if not self.affiliate_enabled:
            return None
        referred_user = await self._require_eligible_user(
            referred_user_id, allow_pending=True
        )
        await self.ensure_profile_in_current_transaction(referred_user_id)
        return await self._attribute_user(
            referred_user=referred_user,
            referral_code=referral_code,
            click_id=click_id,
        )

    async def record_click(
        self, *, referral_code: str, event_id: UUID
    ) -> AffiliateReferralClick:
        if not self.affiliate_enabled:
            raise _disabled()
        code = _normalize_code(referral_code)
        async with self.session.begin():
            profile = await self.session.scalar(
                select(AffiliateProfile).where(
                    AffiliateProfile.referral_code == code,
                    AffiliateProfile.status == "ACTIVE",
                )
            )
            if profile is None:
                raise _not_found()
            try:
                await self._require_eligible_user(profile.user_id)
            except DomainError as exc:
                if exc.status_code == 403:
                    raise _not_found() from exc
                raise
            existing = await self.session.get(AffiliateReferralClick, event_id)
            if existing is not None:
                if (
                    existing.affiliate_user_id != profile.user_id
                    or existing.referral_code_snapshot != code
                ):
                    raise _conflict("Mã sự kiện đã được dùng cho lượt truy cập khác.")
                return existing
            click = AffiliateReferralClick(
                id=event_id,
                affiliate_user_id=profile.user_id,
                referral_code_snapshot=code,
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(click)
                    await self.session.flush()
            except IntegrityError as exc:
                existing = await self.session.get(AffiliateReferralClick, event_id)
                if (
                    existing is not None
                    and existing.affiliate_user_id == profile.user_id
                    and existing.referral_code_snapshot == code
                ):
                    return existing
                raise _conflict(
                    "Mã sự kiện đã được dùng cho lượt truy cập khác."
                ) from exc
            return click

    async def claim_referral(
        self,
        *,
        referred_user_id: UUID,
        referral_code: str,
        click_id: UUID | None = None,
    ) -> AffiliateAttribution:
        if not self.affiliate_enabled:
            raise _disabled()
        code = _normalize_code(referral_code)
        async with self.session.begin():
            referred_user = await self._require_eligible_user(referred_user_id)
            await self.ensure_profile_in_current_transaction(
                referred_user_id, allow_pending=False
            )
            return await self._attribute_user(
                referred_user=referred_user,
                referral_code=code,
                click_id=click_id,
            )

    async def record_commission_in_current_transaction(
        self,
        *,
        source_reference: str,
        referred_user_id: UUID,
        service_code: str,
        amount_minor: int,
        earned_at: datetime | None = None,
    ) -> AffiliateCommission | None:
        """Create one commission record inside the paid-service transaction."""
        if not self.affiliate_enabled or not self.direct_commission_enabled:
            return None
        source = source_reference.strip()
        service = service_code.strip().upper()
        if (
            not source
            or len(source) > 160
            or not 1 <= len(service) <= 64
            or not service.replace("_", "").isalnum()
            or type(amount_minor) is not int
            or amount_minor <= 0
        ):
            raise DomainError(
                code="AFFILIATE_COMMISSION_INVALID",
                message="Giao dịch không đủ dữ liệu để tính hoa hồng.",
                status_code=422,
            )

        existing = await self.session.scalar(
            select(AffiliateCommission).where(
                AffiliateCommission.source_reference == source
            )
        )
        if existing is not None:
            if (
                existing.referred_user_id != referred_user_id
                or existing.service_code != service
                or existing.amount_minor != amount_minor
            ):
                raise _conflict("Giao dịch nguồn đã được gắn với hoa hồng khác.")
            return existing

        now = _utc(earned_at or self._clock())
        attribution = await self.session.scalar(
            select(AffiliateAttribution)
            .where(
                AffiliateAttribution.referred_user_id == referred_user_id,
                AffiliateAttribution.attributed_at <= now,
                AffiliateAttribution.expires_at >= now,
            )
            .with_for_update()
        )
        if attribution is None:
            return None
        profile = await self.session.get(
            AffiliateProfile, attribution.affiliate_user_id
        )
        if profile is None or profile.status != "ACTIVE":
            return None
        try:
            await self._require_eligible_user(profile.user_id)
        except DomainError as exc:
            if exc.status_code == 403:
                return None
            raise

        current = await self._current_rule_set_in_transaction()
        if current is None:
            raise DomainError(
                code="AFFILIATE_RULES_UNAVAILABLE",
                message="Chính sách hoa hồng hiện chưa được cấu hình.",
                status_code=503,
            )
        rate = next(
            (
                row.direct_rate_basis_points
                for row in current.rates
                if row.service_code == service
            ),
            0,
        )
        if not current.rule_set.enabled:
            rate = 0
        commission_amount = amount_minor * rate // 10_000
        status = "PENDING" if commission_amount > 0 else "SUPPRESSED"
        commission = AffiliateCommission(
            affiliate_user_id=profile.user_id,
            referred_user_id=referred_user_id,
            rule_set_id=current.rule_set.id,
            rule_set_version=current.rule_set.version_no,
            service_code=service,
            source_reference=source,
            amount_minor=amount_minor,
            commission_amount_minor=commission_amount,
            rate_basis_points=rate,
            status=status,
            earned_at=now,
            hold_until=now + timedelta(days=current.rule_set.hold_days),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(commission)
                await self.session.flush()
        except IntegrityError as exc:
            existing = await self.session.scalar(
                select(AffiliateCommission).where(
                    AffiliateCommission.source_reference == source
                )
            )
            if (
                existing is not None
                and existing.referred_user_id == referred_user_id
                and existing.service_code == service
                and existing.amount_minor == amount_minor
            ):
                return existing
            raise _conflict(
                "Giao dịch nguồn đã được gắn với hoa hồng khác."
            ) from exc

        self.session.add(
            AuditLog(
                actor_type=AuditActorType.SERVICE,
                actor_service="affiliate",
                action="affiliate.commission.recorded",
                resource_type="affiliate_commission",
                resource_id=str(commission.id),
                after_json={
                    "source_reference": source,
                    "service_code": service,
                    "amount_minor": amount_minor,
                    "commission_amount_minor": commission_amount,
                    "rule_set_version": current.rule_set.version_no,
                    "status": status,
                },
            )
        )
        await self.session.flush()
        return commission

    async def list_commissions(
        self,
        *,
        affiliate_user_id: UUID | None = None,
        commission_status: str | None = None,
        limit: int = 100,
    ) -> tuple[AffiliateCommission, ...]:
        async with self.session.begin():
            statement = select(AffiliateCommission).order_by(
                AffiliateCommission.created_at.desc(), AffiliateCommission.id
            )
            if affiliate_user_id is not None:
                statement = statement.where(
                    AffiliateCommission.affiliate_user_id == affiliate_user_id
                )
            if commission_status is not None:
                statement = statement.where(
                    AffiliateCommission.status == commission_status
                )
            return tuple(await self.session.scalars(statement.limit(limit)))

    async def list_owned_commissions(
        self, *, user_id: UUID, commission_status: str | None = None, limit: int = 100
    ) -> tuple[AffiliateCommission, ...]:
        async with self.session.begin():
            await self._require_eligible_user(user_id)
            return tuple(
                await self.session.scalars(
                    select(AffiliateCommission)
                    .where(AffiliateCommission.affiliate_user_id == user_id)
                    .where(
                        AffiliateCommission.status == commission_status
                        if commission_status is not None
                        else True
                    )
                    .order_by(
                        AffiliateCommission.created_at.desc(), AffiliateCommission.id
                    )
                    .limit(limit)
                )
            )

    async def list_owned_referrals(
        self, *, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> tuple[AffiliateReferralSummary, ...]:
        async with self.session.begin():
            rows = await self.session.execute(
                select(
                    AffiliateAttribution,
                    func.count(AffiliateCommission.id),
                    func.coalesce(func.sum(AffiliateCommission.amount_minor), 0),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    AffiliateCommission.status.in_(
                                        ("PENDING", "ON_HOLD", "AVAILABLE", "REVERSED")
                                    ),
                                    AffiliateCommission.commission_amount_minor,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                )
                .outerjoin(
                    AffiliateCommission,
                    and_(
                        AffiliateCommission.affiliate_user_id
                        == AffiliateAttribution.affiliate_user_id,
                        AffiliateCommission.referred_user_id
                        == AffiliateAttribution.referred_user_id,
                    ),
                )
                .where(AffiliateAttribution.affiliate_user_id == user_id)
                .group_by(AffiliateAttribution.id)
                .order_by(
                    AffiliateAttribution.attributed_at.desc(),
                    AffiliateAttribution.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
            return tuple(
                AffiliateReferralSummary(
                    id=row[0].id,
                    attributed_at=row[0].attributed_at,
                    expires_at=row[0].expires_at,
                    conversion_count=int(row[1] or 0),
                    revenue_minor=int(row[2] or 0),
                    commission_amount_minor=int(row[3] or 0),
                )
                for row in rows.all()
            )

    async def list_profiles(
        self,
        *,
        search: str | None = None,
        profile_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[AffiliateProfileAdminSummary, ...]:
        async with self.session.begin():
            statement = self._profile_admin_statement()
            if profile_status is not None:
                statement = statement.where(AffiliateProfile.status == profile_status)
            query = (search or "").strip()
            if query:
                pattern = f"%{query}%"
                statement = statement.where(
                    or_(
                        AffiliateProfile.referral_code.ilike(pattern),
                        User.email.ilike(pattern),
                        cast(AffiliateProfile.user_id, String).ilike(pattern),
                    )
                )
            rows = await self.session.execute(
                statement.order_by(
                    AffiliateProfile.created_at.desc(), AffiliateProfile.user_id
                )
                .offset(offset)
                .limit(limit)
            )
            return tuple(self._to_profile_admin_summary(row) for row in rows.all())

    async def get_profile_admin_detail(
        self, user_id: UUID
    ) -> AffiliateProfileAdminSummary:
        async with self.session.begin():
            result = await self.session.execute(
                self._profile_admin_statement().where(
                    AffiliateProfile.user_id == user_id
                )
            )
            row = result.first()
            if row is None:
                raise _not_found()
            return self._to_profile_admin_summary(row)

    async def set_profile_status(
        self,
        *,
        user_id: UUID,
        actor_user_id: UUID,
        profile_status: str,
        reason: str,
    ) -> AffiliateProfileAdminSummary:
        normalized_reason = reason.strip()
        if profile_status not in {"ACTIVE", "SUSPENDED"} or not (
            10 <= len(normalized_reason) <= 500
        ):
            raise DomainError(
                code="AFFILIATE_PROFILE_REVIEW_INVALID",
                message=(
                    "Tráº¡ng thÃ¡i hoáº·c lÃ½ do xá»­ lÃ½ Affiliate khÃ´ng há»£p lá»‡."
                ),
                status_code=422,
            )
        async with self.session.begin():
            profile = await self.session.scalar(
                select(AffiliateProfile)
                .where(AffiliateProfile.user_id == user_id)
                .with_for_update()
            )
            if profile is None:
                raise _not_found()
            if profile_status == "ACTIVE":
                await self._require_eligible_user(user_id, allow_pending=False)
            previous_status = profile.status
            if previous_status != profile_status:
                profile.status = profile_status
                self.session.add(
                    AuditLog(
                        actor_user_id=actor_user_id,
                        actor_type=AuditActorType.USER,
                        action=(
                            "affiliate.profile.suspended"
                            if profile_status == "SUSPENDED"
                            else "affiliate.profile.restored"
                        ),
                        resource_type="affiliate_profile",
                        resource_id=str(user_id),
                        before_json={"status": previous_status},
                        after_json={
                            "status": profile_status,
                            "reason": normalized_reason,
                        },
                    )
                )
                await self.session.flush()
            result = await self.session.execute(
                self._profile_admin_statement().where(
                    AffiliateProfile.user_id == user_id
                )
            )
            row = result.first()
            assert row is not None
            return self._to_profile_admin_summary(row)

    @staticmethod
    def _profile_admin_statement():
        click_count = (
            select(func.count())
            .select_from(AffiliateReferralClick)
            .where(AffiliateReferralClick.affiliate_user_id == AffiliateProfile.user_id)
            .correlate(AffiliateProfile)
            .scalar_subquery()
        )
        attributed_user_count = (
            select(func.count())
            .select_from(AffiliateAttribution)
            .where(AffiliateAttribution.affiliate_user_id == AffiliateProfile.user_id)
            .correlate(AffiliateProfile)
            .scalar_subquery()
        )
        return select(AffiliateProfile, click_count, attributed_user_count).join(
            User, User.id == AffiliateProfile.user_id
        )

    @staticmethod
    def _to_profile_admin_summary(row) -> AffiliateProfileAdminSummary:
        profile = row[0]
        return AffiliateProfileAdminSummary(
            user_id=profile.user_id,
            referral_code=profile.referral_code,
            status=profile.status,
            created_at=profile.created_at,
            click_count=int(row[1] or 0),
            attributed_user_count=int(row[2] or 0),
        )

    async def approve_commission(
        self, *, commission_id: UUID, actor_user_id: UUID
    ) -> AffiliateCommission:
        async with self.session.begin():
            commission = await self._commission_for_update(commission_id)
            if commission.status in {"ON_HOLD", "AVAILABLE"}:
                return commission
            if commission.status != "PENDING":
                raise _conflict("Hoa hồng không còn ở trạng thái chờ duyệt.")
            if commission.affiliate_user_id == actor_user_id:
                raise DomainError(
                    code="AFFILIATE_SELF_APPROVAL_FORBIDDEN",
                    message="Người nhận không thể tự phê duyệt hoa hồng.",
                    status_code=403,
                )
            now = _utc(self._clock())
            previous_status = commission.status
            commission.reviewed_by_user_id = actor_user_id
            commission.approved_at = now
            if commission.hold_until > now:
                commission.status = "ON_HOLD"
                self._audit_commission_action(
                    commission,
                    actor_user_id,
                    "affiliate.commission.approved_on_hold",
                    {
                        "status": "ON_HOLD",
                        "hold_until": commission.hold_until.isoformat(),
                    },
                    before_status=previous_status,
                )
                self._notify_commission(
                    commission,
                    event="approved",
                    event_type="AFFILIATE_COMMISSION_ON_HOLD",
                    title="Hoa hồng đã được duyệt",
                    body="Hoa hồng đang trong thời gian đối soát trước khi khả dụng.",
                )
            else:
                await self._make_commission_available(commission, actor_user_id)
                self._audit_commission_action(
                    commission,
                    actor_user_id,
                    "affiliate.commission.approved",
                    {
                        "status": "AVAILABLE",
                        "amount_minor": commission.commission_amount_minor,
                    },
                    before_status=previous_status,
                )
                self._notify_commission(
                    commission,
                    event="available",
                    event_type="AFFILIATE_COMMISSION_AVAILABLE",
                    title="Hoa hồng đã được ghi có",
                    body="Hoa hồng đã được chuyển vào số dư khả dụng.",
                )
            await self.session.flush()
            return commission

    async def reject_commission(
        self, *, commission_id: UUID, actor_user_id: UUID, reason: str
    ) -> AffiliateCommission:
        reason = _validate_reason(reason)
        async with self.session.begin():
            commission = await self._commission_for_update(commission_id)
            if commission.status == "REJECTED":
                if commission.review_reason == reason:
                    return commission
                raise _conflict("Hoa hồng đã bị từ chối với lý do khác.")
            if commission.status != "PENDING":
                raise _conflict("Chỉ hoa hồng đang chờ duyệt mới có thể bị từ chối.")
            if commission.affiliate_user_id == actor_user_id:
                raise DomainError(
                    code="AFFILIATE_SELF_REVIEW_FORBIDDEN",
                    message="Người nhận không thể tự xử lý hoa hồng của mình.",
                    status_code=403,
                )
            previous_status = commission.status
            commission.status = "REJECTED"
            commission.reviewed_by_user_id = actor_user_id
            commission.approved_at = None
            commission.review_reason = reason
            self._audit_commission_action(
                commission,
                actor_user_id,
                "affiliate.commission.rejected",
                {"status": "REJECTED", "reason": reason},
                before_status=previous_status,
            )
            self._notify_commission(
                commission,
                event="rejected",
                event_type="AFFILIATE_COMMISSION_REJECTED",
                title="Hoa hồng chưa được duyệt",
                body=reason,
            )
            await self.session.flush()
            return commission

    async def release_matured_commissions(self, *, limit: int = 100) -> int:
        async with self.session.begin():
            now = _utc(self._clock())
            commissions = tuple(
                await self.session.scalars(
                    select(AffiliateCommission)
                    .where(
                        AffiliateCommission.status == "ON_HOLD",
                        AffiliateCommission.hold_until <= now,
                    )
                    .order_by(AffiliateCommission.hold_until, AffiliateCommission.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            )
            for commission in commissions:
                previous_status = commission.status
                actor_id = commission.reviewed_by_user_id
                await self._make_commission_available(commission, actor_id)
                self._audit_commission_action(
                    commission,
                    actor_id,
                    "affiliate.commission.hold_released",
                    {
                        "status": "AVAILABLE",
                        "amount_minor": commission.commission_amount_minor,
                    },
                    before_status=previous_status,
                )
                self._notify_commission(
                    commission,
                    event="available",
                    event_type="AFFILIATE_COMMISSION_AVAILABLE",
                    title="Hoa hồng đã được ghi có",
                    body="Thời gian đối soát đã kết thúc; hoa hồng đã khả dụng.",
                )
            await self.session.flush()
            return len(commissions)

    async def reverse_commission(
        self, *, commission_id: UUID, actor_user_id: UUID, reason: str
    ) -> AffiliateCommission:
        reason = _validate_reason(reason)
        async with self.session.begin():
            commission = await self._commission_for_update(commission_id)
            if commission.status == "REVERSED":
                if commission.reversal_reason == reason:
                    return commission
                raise _conflict("Hoa hồng đã được đảo với lý do khác.")
            if commission.status not in {"PENDING", "ON_HOLD", "AVAILABLE"}:
                raise _conflict("Hoa hồng này không thể được đảo.")
            if commission.affiliate_user_id == actor_user_id:
                raise DomainError(
                    code="AFFILIATE_SELF_REVIEW_FORBIDDEN",
                    message="Người nhận không thể tự đảo hoa hồng của mình.",
                    status_code=403,
                )
            previous_status = commission.status
            if commission.status == "AVAILABLE":
                ledger = FinanceLedger(self.session)
                available, _ = await ledger.user_accounts(commission.affiliate_user_id)
                expense = await ledger.platform_account("COMMISSION_EXPENSE")
                journal = await ledger.transfer(
                    source_account_id=available.id,
                    target_account_id=expense.id,
                    amount_minor=commission.commission_amount_minor,
                    transaction_type="COMMISSION_REVERSAL",
                    idempotency_key=f"affiliate-commission-reversal:{commission.id}",
                    source_reference=f"affiliate-commission-reversal:{commission.id}",
                    description="Đảo hoa hồng Affiliate",
                    actor_user_id=actor_user_id,
                )
                commission.reversal_journal_id = journal.id
            commission.status = "REVERSED"
            commission.reversed_at = _utc(self._clock())
            commission.reversed_by_user_id = actor_user_id
            commission.reversal_reason = reason
            self._audit_commission_action(
                commission,
                actor_user_id,
                "affiliate.commission.reversed",
                {"status": "REVERSED", "reason": reason},
                before_status=previous_status,
            )
            self._notify_commission(
                commission,
                event="reversed",
                event_type="AFFILIATE_COMMISSION_REVERSED",
                title="Hoa hồng đã được điều chỉnh",
                body=reason,
            )
            await self.session.flush()
            return commission

    async def _make_commission_available(
        self, commission: AffiliateCommission, actor_user_id: UUID | None
    ) -> None:
        ledger = FinanceLedger(self.session)
        available, _ = await ledger.user_accounts(commission.affiliate_user_id)
        expense = await ledger.platform_account("COMMISSION_EXPENSE")
        journal = await ledger.transfer(
            source_account_id=expense.id,
            target_account_id=available.id,
            amount_minor=commission.commission_amount_minor,
            transaction_type="COMMISSION_CREDIT",
            idempotency_key=f"affiliate-commission-credit:{commission.id}",
            source_reference=f"affiliate-commission:{commission.id}",
            description="Hoa hồng Affiliate đã duyệt",
            actor_user_id=actor_user_id,
        )
        commission.finance_journal_id = journal.id
        commission.status = "AVAILABLE"

    async def _commission_for_update(self, commission_id: UUID) -> AffiliateCommission:
        commission = await self.session.scalar(
            select(AffiliateCommission)
            .where(AffiliateCommission.id == commission_id)
            .with_for_update()
        )
        if commission is None:
            raise _not_found()
        return commission

    def _audit_commission_action(
        self,
        commission: AffiliateCommission,
        actor_user_id: UUID | None,
        action: str,
        after: dict[str, object],
        *,
        before_status: str | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                actor_type=(
                    AuditActorType.USER if actor_user_id else AuditActorType.SERVICE
                ),
                actor_service="affiliate" if actor_user_id is None else None,
                action=action,
                resource_type="affiliate_commission",
                resource_id=str(commission.id),
                before_json={"status": before_status or commission.status},
                after_json=after,
            )
        )

    def _notify_commission(
        self,
        commission: AffiliateCommission,
        *,
        event: str,
        event_type: str,
        title: str,
        body: str,
    ) -> None:
        event_id = uuid5(NAMESPACE_URL, f"affiliate-commission:{commission.id}:{event}")
        self.session.add(
            Notification(
                user_id=commission.affiliate_user_id,
                source_event_id=event_id,
                type=event_type,
                title=title,
                body=body,
                data_json={
                    "commissionId": str(commission.id),
                    "amountMinor": commission.commission_amount_minor,
                    "actionPath": "/affiliate",
                },
                created_at=_utc(self._clock()),
            )
        )

    async def _attribute_user(
        self,
        *,
        referred_user: User,
        referral_code: str,
        click_id: UUID | None,
    ) -> AffiliateAttribution:
        code = _normalize_code(referral_code)
        referred_user_id = referred_user.id
        existing = await self.session.scalar(
            select(AffiliateAttribution)
            .where(AffiliateAttribution.referred_user_id == referred_user_id)
            .with_for_update()
        )
        if existing is not None:
            referrer = await self.session.get(
                AffiliateProfile, existing.affiliate_user_id
            )
            if referrer is not None and referrer.referral_code == code:
                return existing
            raise _conflict("Tài khoản đã được gắn với mã giới thiệu khác.")

        referrer = await self.session.scalar(
            select(AffiliateProfile).where(
                AffiliateProfile.referral_code == code,
                AffiliateProfile.status == "ACTIVE",
            )
        )
        if referrer is None:
            raise _not_found()
        if referrer.user_id == referred_user_id:
            raise _conflict("Không thể tự sử dụng mã giới thiệu của mình.")
        try:
            await self._require_eligible_user(referrer.user_id, allow_pending=False)
        except DomainError as exc:
            if exc.status_code == 403:
                raise _not_found() from exc
            raise

        click_at: datetime | None = None
        if click_id is not None:
            click = await self.session.get(AffiliateReferralClick, click_id)
            if (
                click is None
                or click.affiliate_user_id != referrer.user_id
                or click.referral_code_snapshot != code
            ):
                raise _conflict("Lượt giới thiệu không khớp với mã đã nhập.")
            click_at = _utc(click.created_at)

        current = await self._current_rule_set_in_transaction()
        if current is None:
            raise DomainError(
                code="AFFILIATE_RULES_UNAVAILABLE",
                message="Chính sách giới thiệu hiện chưa được cấu hình.",
                status_code=503,
            )
        now = _utc(self._clock())
        attributed_at = click_at or _utc(referred_user.created_at)
        expires_at = attributed_at + timedelta(
            days=current.rule_set.attribution_window_days
        )
        if now > expires_at:
            raise _conflict("Thời hạn ghi nhận mã giới thiệu đã kết thúc.")

        attribution = AffiliateAttribution(
            affiliate_user_id=referrer.user_id,
            referred_user_id=referred_user_id,
            referral_click_id=click_id,
            referral_code_snapshot=code,
            attributed_at=attributed_at,
            expires_at=expires_at,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(attribution)
                await self.session.flush()
        except IntegrityError as exc:
            existing = await self.session.scalar(
                select(AffiliateAttribution).where(
                    AffiliateAttribution.referred_user_id == referred_user_id
                )
            )
            if existing is not None and existing.affiliate_user_id == referrer.user_id:
                return existing
            raise _conflict(
                "Tài khoản đã được gắn với mã giới thiệu khác."
            ) from exc
        return attribution

    async def current_rules(self) -> CommissionRuleSetView | None:
        async with self.session.begin():
            return await self._current_rule_set_in_transaction()

    async def list_rule_sets(
        self, *, limit: int = 100
    ) -> tuple[CommissionRuleSetView, ...]:
        async with self.session.begin():
            rows = list(
                await self.session.scalars(
                    select(AffiliateCommissionRuleSet)
                    .order_by(AffiliateCommissionRuleSet.version_no.desc())
                    .limit(limit)
                )
            )
            result = []
            for row in rows:
                rates = tuple(
                    await self.session.scalars(
                        select(AffiliateCommissionRate)
                        .where(AffiliateCommissionRate.rule_set_id == row.id)
                        .order_by(AffiliateCommissionRate.service_code)
                    )
                )
                result.append(CommissionRuleSetView(row, rates))
            return tuple(result)

    async def create_rule_set(
        self,
        *,
        actor_user_id: UUID,
        enabled: bool,
        attribution_window_days: int,
        hold_days: int,
        rates: tuple[tuple[str, int], ...],
    ) -> CommissionRuleSetView:
        _validate_rule_input(attribution_window_days, hold_days, rates)
        async with self.session.begin():
            latest = await self.session.scalar(
                select(AffiliateCommissionRuleSet)
                .order_by(AffiliateCommissionRuleSet.version_no.desc())
                .limit(1)
                .with_for_update()
            )
            version_no = (latest.version_no if latest is not None else 0) + 1
            rule_set = AffiliateCommissionRuleSet(
                version_no=version_no,
                status="DRAFT",
                enabled=enabled,
                attribution_window_days=attribution_window_days,
                hold_days=hold_days,
                level2_enabled=False,
                level2_rate_basis_points=0,
            )
            self.session.add(rule_set)
            await self.session.flush()
            rate_rows = tuple(
                AffiliateCommissionRate(
                    rule_set_id=rule_set.id,
                    service_code=code,
                    direct_rate_basis_points=bps,
                )
                for code, bps in rates
            )
            self.session.add_all(rate_rows)
            self.session.add(
                AuditLog(
                    actor_user_id=actor_user_id,
                    actor_type=AuditActorType.USER,
                    action="affiliate.rules.created",
                    resource_type="affiliate_rule_set",
                    resource_id=str(rule_set.id),
                    after_json={
                        "version": version_no,
                        "enabled": enabled,
                        "attribution_window_days": attribution_window_days,
                        "hold_days": hold_days,
                        "level2_enabled": False,
                        "rates": [
                            {"service_code": code, "direct_rate_basis_points": bps}
                            for code, bps in rates
                        ],
                    },
                )
            )
            await self.session.flush()
            return CommissionRuleSetView(rule_set, rate_rows)

    async def publish_rule_set(
        self, *, actor_user_id: UUID, rule_set_id: UUID
    ) -> CommissionRuleSetView:
        async with self.session.begin():
            rule_set = await self.session.scalar(
                select(AffiliateCommissionRuleSet)
                .where(AffiliateCommissionRuleSet.id == rule_set_id)
                .with_for_update()
            )
            if rule_set is None:
                raise _not_found()
            if rule_set.status != "DRAFT":
                raise _conflict(
                    "Chỉ có thể phát hành phiên bản đang ở trạng thái nháp."
                )
            now = _utc(self._clock())
            rule_set.status = "PUBLISHED"
            rule_set.effective_from = now
            rule_set.published_at = now
            rule_set.published_by_user_id = actor_user_id
            rates = tuple(
                await self.session.scalars(
                    select(AffiliateCommissionRate)
                    .where(AffiliateCommissionRate.rule_set_id == rule_set.id)
                    .order_by(AffiliateCommissionRate.service_code)
                )
            )
            self.session.add(
                AuditLog(
                    actor_user_id=actor_user_id,
                    actor_type=AuditActorType.USER,
                    action="affiliate.rules.published",
                    resource_type="affiliate_rule_set",
                    resource_id=str(rule_set.id),
                    after_json={
                        "version": rule_set.version_no,
                        "enabled": rule_set.enabled,
                        "effective_from": now.isoformat(),
                    },
                )
            )
            await self.session.flush()
            return CommissionRuleSetView(rule_set, rates)

    async def _current_rule_set_in_transaction(
        self,
    ) -> CommissionRuleSetView | None:
        now = _utc(self._clock())
        rule_set = await self.session.scalar(
            select(AffiliateCommissionRuleSet)
            .where(
                AffiliateCommissionRuleSet.status == "PUBLISHED",
                AffiliateCommissionRuleSet.effective_from.is_not(None),
                AffiliateCommissionRuleSet.effective_from <= now,
            )
            .order_by(
                AffiliateCommissionRuleSet.effective_from.desc(),
                AffiliateCommissionRuleSet.version_no.desc(),
            )
            .limit(1)
        )
        if rule_set is None:
            return None
        rates = tuple(
            await self.session.scalars(
                select(AffiliateCommissionRate)
                .where(AffiliateCommissionRate.rule_set_id == rule_set.id)
                .order_by(AffiliateCommissionRate.service_code)
            )
        )
        return CommissionRuleSetView(rule_set, rates)

    async def _require_eligible_user(
        self, user_id: UUID, *, allow_pending: bool = False
    ) -> User:
        user = await self.session.scalar(select(User).where(User.id == user_id))
        if (
            user is None
            or user.status
            not in (
                {UserStatus.ACTIVE, UserStatus.PENDING}
                if allow_pending
                else {UserStatus.ACTIVE}
            )
            or user.disabled_at is not None
            or user.deleted_at is not None
        ):
            raise _forbidden()
        role_codes = set(
            await self.session.scalars(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
            )
        )
        if role_codes != {"USER"}:
            raise _forbidden()
        employee_id = await self.session.scalar(
            select(Employee.id).where(Employee.user_id == user_id).limit(1)
        )
        if employee_id is not None:
            raise _forbidden()
        return user

    async def record_commission(
        self,
        *,
        source_reference: str,
        referred_user_id: UUID,
        service_code: str,
        amount_minor: int,
        earned_at: datetime | None = None,
    ) -> AffiliateCommission | None:
        if not self.affiliate_enabled:
            return None
        async with self.session.begin():
            return await self.record_commission_in_current_transaction(
                source_reference=source_reference,
                referred_user_id=referred_user_id,
                service_code=service_code,
                amount_minor=amount_minor,
                earned_at=earned_at,
            )

    async def _commission_total(self, user_id: UUID, status: str) -> int:
        total = await self.session.scalar(
            select(
                func.coalesce(func.sum(AffiliateCommission.commission_amount_minor), 0)
            ).where(
                AffiliateCommission.affiliate_user_id == user_id,
                AffiliateCommission.status == status,
            )
        )
        return int(total or 0)


def _normalize_code(value: str) -> str:
    code = value.strip().upper()
    if not 8 <= len(code) <= 32 or not code.replace("-", "").isalnum():
        raise DomainError(
            code="AFFILIATE_CODE_INVALID",
            message="Mã giới thiệu không hợp lệ.",
            status_code=422,
        )
    return code


def _validate_rule_input(
    attribution_window_days: int,
    hold_days: int,
    rates: tuple[tuple[str, int], ...],
) -> None:
    if not 0 <= attribution_window_days <= 3650 or not 0 <= hold_days <= 3650:
        raise DomainError(
            code="AFFILIATE_RULE_INVALID",
            message="Thời hạn chính sách không hợp lệ.",
            status_code=422,
        )
    seen: set[str] = set()
    for code, rate in rates:
        normalized = code.strip().upper()
        if (
            not 1 <= len(normalized) <= 64
            or not normalized.replace("_", "").isalnum()
            or normalized in seen
            or type(rate) is not int
            or not 0 <= rate <= 10_000
        ):
            raise DomainError(
                code="AFFILIATE_RULE_INVALID",
                message="Quy tắc hoa hồng không hợp lệ.",
                status_code=422,
            )
        seen.add(normalized)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _forbidden() -> DomainError:
    return DomainError(
        code="AFFILIATE_FORBIDDEN",
        message="Tính năng Affiliate chỉ dành cho tài khoản người dùng thông thường.",
        status_code=403,
    )


def _not_found() -> DomainError:
    return DomainError(
        code="AFFILIATE_NOT_FOUND",
        message="Không tìm thấy hồ sơ hoặc mã giới thiệu.",
        status_code=404,
    )


def _conflict(message: str) -> DomainError:
    return DomainError(
        code="AFFILIATE_CONFLICT",
        message=message,
        status_code=409,
    )


def _disabled() -> DomainError:
    return DomainError(
        code="AFFILIATE_DISABLED",
        message="Tính năng Affiliate hiện chưa được kích hoạt.",
        status_code=403,
    )


def _validate_reason(reason: str) -> str:
    normalized = " ".join(reason.split())
    if not 10 <= len(normalized) <= 1000:
        raise DomainError(
            code="AFFILIATE_REVIEW_REASON_INVALID",
            message="Lý do xử lý cần có từ 10 đến 1.000 ký tự.",
            status_code=422,
        )
    return normalized
