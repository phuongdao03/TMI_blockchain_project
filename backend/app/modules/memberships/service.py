from datetime import UTC, datetime, timedelta
from hashlib import sha256
from math import ceil
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.identity import public_user_identity
from app.modules.community.models import CommunityMemberRestriction, CommunityProfile
from app.modules.community.repository import CommunityRepository
from app.modules.memberships.cycle import active_membership_cycle
from app.modules.memberships.models import (
    CommunityChatMessage,
    MembershipBenefitRequest,
    MembershipChatRoomAccess,
    MembershipDiamondApplication,
    MembershipPlan,
    MembershipPurchase,
    UserMembership,
)
from app.modules.notifications.models import Notification
from app.modules.payments.errors import (
    PaymentConflictError,
    PaymentForbiddenError,
    PaymentNotFoundError,
)
from app.modules.users.models import UserProfile
from app.modules.wallet.models import WalletJournal
from app.modules.wallet.service import WalletLedger, valid_key

TIERS = {"MEMBER": 0, "SILVER": 1, "COMPANION": 2, "PRESTIGE": 3}


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class MembershipService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def remove_message(self, principal: AuthPrincipal, identifier: UUID) -> None:
        async with self.session.begin():
            message = await self.session.get(CommunityChatMessage, identifier)
            if message is None:
                raise PaymentNotFoundError()
            if message.user_id != principal.user_id:
                AuthorizationPolicy.require_capability(
                    principal,
                    PolicyRequirement("community.moderate"),
                    PaymentForbiddenError,
                )
            message.deleted_at = datetime.now(UTC)
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action="community.chat.removed",
                resource_type="community_chat_message",
                resource_id=str(identifier),
            )

    async def retire_plan(self, principal: AuthPrincipal, identifier: UUID) -> None:
        AuthorizationPolicy.require_capability(
            principal, PolicyRequirement("memberships.manage"), PaymentForbiddenError
        )
        async with self.session.begin():
            plan = await self.session.get(MembershipPlan, identifier)
            if plan is None:
                raise PaymentNotFoundError()
            plan.active = False
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action="membership.plan.retired",
                resource_type="membership_plan",
                resource_id=str(identifier),
            )

    async def current(self, user_id: UUID) -> dict[str, object]:
        membership = await self.session.get(UserMembership, user_id)
        active = membership is not None and utc(membership.expires_at) > datetime.now(
            UTC
        )
        return {
            "tier": membership.tier if active and membership else "MEMBER",
            "expires_at": utc(membership.expires_at) if active and membership else None,
            "status": "ACTIVE" if active else "FREE",
            "member_number": f"THV-{user_id.hex.upper()}",
        }

    async def public_plans(self) -> list[MembershipPlan]:
        return list(
            await self.session.scalars(
                select(MembershipPlan)
                .where(MembershipPlan.active.is_(True))
                .order_by(MembershipPlan.amount_minor, MembershipPlan.tier)
            )
        )

    async def overview(self, user_id: UUID) -> dict[str, object]:
        async with self.session.begin():
            current = await self.current(user_id)
            plans = await self.public_plans()
            purchases = list(
                await self.session.scalars(
                    select(MembershipPurchase)
                    .where(MembershipPurchase.user_id == user_id)
                    .order_by(MembershipPurchase.created_at.desc())
                    .limit(20)
                )
            )
            return {**current, "plans": plans, "purchases": purchases}

    async def publish(
        self,
        principal: AuthPrincipal,
        *,
        name: str,
        tier: str,
        amount_minor: int,
        duration_days: int,
        description: str = "",
        benefits: list[str] | None = None,
        conditions: str = "",
    ) -> MembershipPlan:
        AuthorizationPolicy.require_capability(
            principal, PolicyRequirement("memberships.manage"), PaymentForbiddenError
        )
        if (
            tier not in {"SILVER", "COMPANION", "PRESTIGE"}
            or not name.strip()
            or not 0 < amount_minor <= 1_000_000_000
            or not 1 <= duration_days <= 3660
            or len(description.strip()) > 500
            or len(conditions.strip()) > 1000
            or len(benefits or []) > 20
            or any(
                not item.strip() or len(item.strip()) > 240
                for item in benefits or []
            )
        ):
            raise PaymentConflictError("Thông tin gói thành viên không hợp lệ.")
        async with self.session.begin():
            plan = MembershipPlan(
                name=name.strip(),
                tier=tier,
                amount_minor=amount_minor,
                duration_days=duration_days,
                description=description.strip(),
                benefits=[item.strip() for item in benefits or []],
                conditions=conditions.strip(),
            )
            self.session.add(plan)
            await self.session.flush()
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action="membership.plan.published",
                resource_type="membership_plan",
                resource_id=str(plan.id),
                after={
                    "tier": tier,
                    "amount_minor": amount_minor,
                    "duration_days": duration_days,
                    "description": description.strip(),
                    "benefits": benefits or [],
                },
            )
            await self.session.refresh(plan)
            return plan

    async def quote(
        self,
        user_id: UUID,
        plan_id: UUID,
        *,
        renewal_opt_in: bool = False,
    ) -> dict[str, object]:
        async with self.session.begin():
            return await self._quote(
                user_id, plan_id, renewal_opt_in=renewal_opt_in
            )

    async def _quote(
        self,
        user_id: UUID,
        plan_id: UUID,
        *,
        renewal_opt_in: bool,
    ) -> dict[str, object]:
        plan = await self.session.get(MembershipPlan, plan_id)
        if plan is None or not plan.active:
            raise PaymentNotFoundError("Gói thành viên chưa mở đăng ký.")

        now = datetime.now(UTC)
        membership = await self.session.get(UserMembership, user_id)
        active = membership is not None and utc(membership.expires_at) > now
        current_tier = membership.tier if active and membership else "MEMBER"
        if current_tier not in TIERS or plan.tier not in TIERS:
            raise PaymentConflictError("Cấp thành viên hiện tại không hợp lệ.")

        kind = "NEW"
        credit_minor = 0
        remaining_days = 0
        starts_at = now
        if active and membership:
            if TIERS[plan.tier] < TIERS[current_tier]:
                raise PaymentConflictError(
                    "Không thể hạ cấp khi gói hiện tại còn hiệu lực."
                )
            if plan.tier == current_tier:
                if not renewal_opt_in:
                    raise PaymentConflictError(
                        "Xác nhận gia hạn để nối tiếp thời hạn gói hiện tại."
                    )
                kind = "RENEWAL"
                starts_at = utc(membership.expires_at)
            else:
                kind = "UPGRADE"
                credit_minor, remaining_days = await self._remaining_credit(
                    user_id, membership, now
                )
                if credit_minor >= plan.amount_minor:
                    raise PaymentConflictError(
                        "Giá trị còn lại vượt giá gói mới; vui lòng liên hệ "
                        "quản trị viên."
                    )
        expiry = starts_at + timedelta(days=plan.duration_days)
        approval_required = False
        if plan.tier == "PRESTIGE":
            prior_paid_diamond = await self.session.scalar(
                select(MembershipPurchase.id)
                .where(
                    MembershipPurchase.user_id == user_id,
                    MembershipPurchase.tier == "PRESTIGE",
                )
                .limit(1)
            )
            approved_application = await self.session.scalar(
                select(MembershipDiamondApplication.id)
                .where(
                    MembershipDiamondApplication.user_id == user_id,
                    MembershipDiamondApplication.status == "APPROVED",
                )
                .limit(1)
            )
            approval_required = (
                prior_paid_diamond is None and approved_application is None
            )

        return {
            "plan_id": plan.id,
            "name": plan.name,
            "tier": plan.tier,
            "kind": kind,
            "from_tier": current_tier,
            "list_price_minor": plan.amount_minor,
            "credit_minor": credit_minor,
            "amount_due_minor": plan.amount_minor - credit_minor,
            "duration_days": plan.duration_days,
            "remaining_days": remaining_days,
            "expires_at": expiry,
            "approval_required": approval_required,
        }

    async def _remaining_credit(
        self, user_id: UUID, membership: UserMembership, now: datetime
    ) -> tuple[int, int]:
        rows = await self.session.execute(
            select(MembershipPurchase, MembershipPlan.duration_days)
            .join(MembershipPlan, MembershipPlan.id == MembershipPurchase.plan_id)
            .where(
                MembershipPurchase.user_id == user_id,
                MembershipPurchase.tier == membership.tier,
                MembershipPurchase.expires_at <= membership.expires_at,
            )
        )
        cycles = {
            utc(purchase.expires_at): (purchase, duration_days)
            for purchase, duration_days in rows.all()
        }
        current_cycle = cycles.get(utc(membership.expires_at))
        if current_cycle is None or current_cycle[0].plan_id != membership.plan_id:
            raise PaymentConflictError(
                "Không tìm thấy giao dịch gốc để tính giá trị còn lại."
            )

        total_credit = 0
        total_remaining_days = 0
        while current_cycle is not None:
            purchase, duration_days = current_cycle
            cycle_end = utc(purchase.expires_at)
            cycle_start = cycle_end - timedelta(days=duration_days)
            if now >= cycle_end:
                break
            cycle_remaining = min(
                duration_days,
                max(
                    0,
                    ceil(
                        (cycle_end - max(now, cycle_start)).total_seconds() / 86400
                    ),
                ),
            )
            total_remaining_days += cycle_remaining
            total_credit += (
                purchase.list_price_minor
                * cycle_remaining
                // duration_days
            )
            current_cycle = cycles.get(cycle_start)
        return total_credit, total_remaining_days

    async def purchase(
        self,
        user_id: UUID,
        plan_id: UUID,
        key: str,
        *,
        expected_amount_minor: int,
        renewal_opt_in: bool = False,
    ) -> dict[str, object]:
        key = valid_key(key)
        if type(expected_amount_minor) is not int or expected_amount_minor < 0:
            raise PaymentConflictError("Số tiền xác nhận không hợp lệ.")
        reference = f"membership:{user_id}:{sha256(key.encode()).hexdigest()}"
        async with self.session.begin():
            await WalletLedger(self.session).lock(user_id)
            replay = await self.session.scalar(
                select(WalletJournal).where(
                    WalletJournal.user_id == user_id,
                    WalletJournal.idempotency_key == key,
                )
            )
            if replay is not None:
                purchase = await self.session.get(MembershipPurchase, replay.id)
                if purchase is None or purchase.plan_id != plan_id:
                    raise PaymentConflictError(
                        "Khóa giao dịch đã được dùng cho khoản khác."
                    )
                if purchase.amount_minor != expected_amount_minor:
                    raise PaymentConflictError(
                        "Số tiền xác nhận không khớp giao dịch đã ghi nhận."
                    )
                return await self.current(user_id)
            now = datetime.now(UTC)
            membership = await self.session.get(UserMembership, user_id)
            await self.session.scalar(
                select(MembershipPlan)
                .where(MembershipPlan.id == plan_id)
                .with_for_update()
            )
            quote = await self._quote(
                user_id, plan_id, renewal_opt_in=renewal_opt_in
            )
            if quote["approval_required"]:
                raise PaymentForbiddenError()
            if expected_amount_minor != quote["amount_due_minor"]:
                raise PaymentConflictError(
                    "Báo giá đã thay đổi; vui lòng xác nhận lại."
                )
            plan = await self.session.get(MembershipPlan, plan_id)
            assert plan is not None
            expiry = quote["expires_at"]
            amount_due_value = quote["amount_due_minor"]
            credit_value = quote["credit_minor"]
            assert isinstance(expiry, datetime)
            assert isinstance(amount_due_value, int)
            assert isinstance(credit_value, int)
            amount_due = amount_due_value
            credit_minor = credit_value
            posting = await WalletLedger(self.session).post(
                user_id=user_id,
                delta=-amount_due,
                kind="PAYMENT",
                key=key,
                reference=reference,
                description=f"Thẻ thành viên: {plan.name}",
            )
            if membership is None:
                membership = UserMembership(
                    user_id=user_id, plan_id=plan.id, tier=plan.tier, expires_at=expiry
                )
                self.session.add(membership)
            else:
                membership.plan_id, membership.tier, membership.expires_at = (
                    plan.id,
                    plan.tier,
                    expiry,
                )
            self.session.add(
                MembershipPurchase(
                    id=posting.id,
                    user_id=user_id,
                    plan_id=plan.id,
                    tier=plan.tier,
                    amount_minor=amount_due,
                    list_price_minor=plan.amount_minor,
                    credit_minor=credit_minor,
                    expires_at=expiry,
                )
            )
            self.session.add(
                Notification(
                    user_id=user_id,
                    source_event_id=posting.id,
                    type="MEMBERSHIP_PURCHASED",
                    title="Thẻ thành viên đã được cập nhật",
                    body=f"Gói {plan.name} có hiệu lực đến {expiry:%d/%m/%Y}.",
                    data_json={"actionPath": "/membership"},
                    created_at=now,
                )
            )
            await self.session.flush()
            return await self.current(user_id)

    async def submit_diamond_application(
        self, principal: AuthPrincipal, statement: str
    ) -> MembershipDiamondApplication:
        statement = statement.strip()
        if not 1 <= len(statement) <= 5000:
            raise PaymentConflictError("Nội dung đăng ký cần từ 1 đến 5.000 ký tự.")
        async with self.session.begin():
            await self.session.scalar(
                select(User.id)
                .where(User.id == principal.user_id)
                .with_for_update()
            )
            application = await self.session.scalar(
                select(MembershipDiamondApplication)
                .where(
                    MembershipDiamondApplication.user_id == principal.user_id,
                    MembershipDiamondApplication.status.in_(
                        ("PENDING", "INFO_REQUESTED")
                    ),
                )
                .with_for_update()
            )
            if application is not None:
                if application.status != "INFO_REQUESTED":
                    if application.statement == statement:
                        return application
                    raise PaymentConflictError(
                        "Đã có đơn Kim cương đang chờ xử lý."
                    )
                before: dict[str, object] | None = {"status": application.status}
                application.statement = statement
                application.status = "PENDING"
                application.decision_note = None
                application.reviewed_by_user_id = None
                application.reviewed_at = None
            else:
                application = MembershipDiamondApplication(
                    user_id=principal.user_id,
                    statement=statement,
                    status="PENDING",
                )
                self.session.add(application)
                before = None
            await self.session.flush()
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action="membership.diamond_application.submitted",
                resource_type="membership_diamond_application",
                resource_id=str(application.id),
                before=before,
                after={"status": application.status},
            )
            await self.session.refresh(application)
            return application

    async def my_diamond_applications(
        self, user_id: UUID
    ) -> list[MembershipDiamondApplication]:
        async with self.session.begin():
            return list(
                await self.session.scalars(
                    select(MembershipDiamondApplication)
                    .where(MembershipDiamondApplication.user_id == user_id)
                    .order_by(MembershipDiamondApplication.created_at.desc())
                )
            )

    async def list_diamond_applications(
        self,
        principal: AuthPrincipal,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MembershipDiamondApplication]:
        AuthorizationPolicy.require_capability(
            principal, PolicyRequirement("memberships.manage"), PaymentForbiddenError
        )
        if status is not None and status not in {
            "PENDING",
            "INFO_REQUESTED",
            "APPROVED",
            "REJECTED",
        }:
            raise PaymentConflictError("Trạng thái đơn Kim cương không hợp lệ.")
        if not 1 <= limit <= 200:
            raise PaymentConflictError("Giới hạn danh sách không hợp lệ.")
        async with self.session.begin():
            query = select(MembershipDiamondApplication).order_by(
                MembershipDiamondApplication.created_at.desc()
            )
            if status is not None:
                query = query.where(MembershipDiamondApplication.status == status)
            return list(await self.session.scalars(query.limit(limit)))

    async def review_diamond_application(
        self,
        principal: AuthPrincipal,
        identifier: UUID,
        *,
        decision: str,
        note: str,
    ) -> MembershipDiamondApplication:
        AuthorizationPolicy.require_capability(
            principal, PolicyRequirement("memberships.manage"), PaymentForbiddenError
        )
        if decision not in {"APPROVED", "REJECTED", "INFO_REQUESTED"}:
            raise PaymentConflictError("Quyết định đơn Kim cương không hợp lệ.")
        note = note.strip()
        if not 1 <= len(note) <= 2000:
            raise PaymentConflictError("Ghi chú cần từ 1 đến 2.000 ký tự.")
        async with self.session.begin():
            application = await self.session.scalar(
                select(MembershipDiamondApplication)
                .where(MembershipDiamondApplication.id == identifier)
                .with_for_update()
            )
            if application is None:
                raise PaymentNotFoundError("Không tìm thấy đơn Kim cương.")
            if application.status not in {"PENDING", "INFO_REQUESTED"}:
                raise PaymentConflictError("Đơn Kim cương đã được xử lý.")
            previous_status = application.status
            application.status = decision
            application.decision_note = note
            application.reviewed_by_user_id = principal.user_id
            application.reviewed_at = datetime.now(UTC)
            await self.session.flush()
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action=f"membership.diamond_application.{decision.lower()}",
                resource_type="membership_diamond_application",
                resource_id=str(identifier),
                before={"status": previous_status},
                after={"status": decision, "note": note},
            )
            await self.session.refresh(application)
            return application

    async def my_benefit_requests(
        self, user_id: UUID
    ) -> list[MembershipBenefitRequest]:
        async with self.session.begin():
            return list(
                await self.session.scalars(
                    select(MembershipBenefitRequest)
                    .where(MembershipBenefitRequest.user_id == user_id)
                    .order_by(MembershipBenefitRequest.created_at.desc())
                    .limit(50)
                )
            )

    async def submit_benefit_request(
        self, principal: AuthPrincipal, *, benefit: str, statement: str
    ) -> MembershipBenefitRequest:
        required_tier = {
            "COLLABORATION_NEED": "COMPANION",
            "ADVISORY_SESSION": "PRESTIGE",
            "FACILITATED_INTRODUCTION": "PRESTIGE",
            "MEMBER_STORY": "PRESTIGE",
        }
        quota = {
            "ADVISORY_SESSION": 1,
            "FACILITATED_INTRODUCTION": 2,
        }
        if benefit not in required_tier:
            raise PaymentConflictError("Loại quyền lợi cần yêu cầu không hợp lệ.")
        statement = statement.strip()
        if not 1 <= len(statement) <= 5000:
            raise PaymentConflictError("Nội dung cần từ 1 đến 5.000 ký tự.")

        async with self.session.begin():
            await self.session.scalar(
                select(User.id)
                .where(User.id == principal.user_id)
                .with_for_update()
            )
            tier, cycle_started_at = await active_membership_cycle(
                self.session, principal.user_id
            )
            if (
                cycle_started_at is None
                or TIERS.get(tier, -1) < TIERS[required_tier[benefit]]
            ):
                raise PaymentForbiddenError()
            if tier == "PRESTIGE":
                approved = await self.session.scalar(
                    select(MembershipDiamondApplication.id)
                    .where(
                        MembershipDiamondApplication.user_id == principal.user_id,
                        MembershipDiamondApplication.status == "APPROVED",
                    )
                    .limit(1)
                )
                if approved is None:
                    raise PaymentForbiddenError()

            pending_info = await self.session.scalar(
                select(MembershipBenefitRequest)
                .where(
                    MembershipBenefitRequest.user_id == principal.user_id,
                    MembershipBenefitRequest.benefit == benefit,
                    MembershipBenefitRequest.cycle_started_at == cycle_started_at,
                    MembershipBenefitRequest.status == "INFO_REQUESTED",
                )
                .with_for_update()
            )
            if pending_info is not None:
                pending_info.statement = statement
                pending_info.status = "PENDING"
                pending_info.decision_note = None
                pending_info.reviewed_by_user_id = None
                pending_info.reviewed_at = None
                await self.session.flush()
                await self.session.refresh(pending_info)
                return pending_info

            active_states = ("PENDING", "INFO_REQUESTED", "APPROVED")
            existing = await self.session.scalar(
                select(MembershipBenefitRequest)
                .where(
                    MembershipBenefitRequest.user_id == principal.user_id,
                    MembershipBenefitRequest.benefit == benefit,
                    MembershipBenefitRequest.cycle_started_at == cycle_started_at,
                    MembershipBenefitRequest.status.in_(active_states),
                )
                .with_for_update()
            )
            if existing is not None:
                if existing.statement == statement:
                    return existing
                if benefit not in quota:
                    raise PaymentConflictError(
                        "Đã có yêu cầu quyền lợi cùng loại đang được xử lý."
                    )

            max_requests = quota.get(benefit)
            if max_requests is not None:
                used = await self.session.scalar(
                    select(func.count(MembershipBenefitRequest.id)).where(
                        MembershipBenefitRequest.user_id == principal.user_id,
                        MembershipBenefitRequest.benefit == benefit,
                        MembershipBenefitRequest.cycle_started_at == cycle_started_at,
                        MembershipBenefitRequest.status != "REJECTED",
                    )
                )
                if int(used or 0) >= max_requests:
                    raise DomainError(
                        code="MEMBERSHIP_BENEFIT_QUOTA_EXHAUSTED",
                        message="Quyền lợi này đã dùng hết lượt trong chu kỳ hiện tại.",
                        status_code=409,
                        details={"benefit": benefit, "quota": max_requests},
                    )

            request = MembershipBenefitRequest(
                user_id=principal.user_id,
                benefit=benefit,
                cycle_started_at=cycle_started_at,
                statement=statement,
                status="PENDING",
            )
            self.session.add(request)
            await self.session.flush()
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action="membership.benefit_request.submitted",
                resource_type="membership_benefit_request",
                resource_id=str(request.id),
                after={"benefit": benefit, "status": request.status},
            )
            await self.session.refresh(request)
            return request

    async def list_benefit_requests(
        self,
        principal: AuthPrincipal,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MembershipBenefitRequest]:
        AuthorizationPolicy.require_capability(
            principal, PolicyRequirement("memberships.manage"), PaymentForbiddenError
        )
        valid_statuses = {
            "PENDING",
            "INFO_REQUESTED",
            "APPROVED",
            "COMPLETED",
            "REJECTED",
        }
        if status is not None and status not in valid_statuses:
            raise PaymentConflictError("Trạng thái yêu cầu quyền lợi không hợp lệ.")
        if not 1 <= limit <= 200:
            raise PaymentConflictError("Giới hạn danh sách không hợp lệ.")
        async with self.session.begin():
            query = select(MembershipBenefitRequest).order_by(
                MembershipBenefitRequest.created_at.desc()
            )
            if status is not None:
                query = query.where(MembershipBenefitRequest.status == status)
            return list(await self.session.scalars(query.limit(limit)))

    async def review_benefit_request(
        self,
        principal: AuthPrincipal,
        identifier: UUID,
        *,
        decision: str,
        note: str,
    ) -> MembershipBenefitRequest:
        AuthorizationPolicy.require_capability(
            principal, PolicyRequirement("memberships.manage"), PaymentForbiddenError
        )
        next_status = {
            "approve": "APPROVED",
            "reject": "REJECTED",
            "request-info": "INFO_REQUESTED",
            "complete": "COMPLETED",
        }.get(decision)
        note = note.strip()
        if next_status is None or not 1 <= len(note) <= 2000:
            raise PaymentConflictError("Quyết định hoặc ghi chú không hợp lệ.")
        async with self.session.begin():
            request = await self.session.scalar(
                select(MembershipBenefitRequest)
                .where(MembershipBenefitRequest.id == identifier)
                .with_for_update()
            )
            if request is None:
                raise PaymentNotFoundError("Không tìm thấy yêu cầu quyền lợi.")
            allowed_from = {
                "approve": {"PENDING", "INFO_REQUESTED"},
                "reject": {"PENDING", "INFO_REQUESTED"},
                "request-info": {"PENDING", "APPROVED"},
                "complete": {"APPROVED"},
            }
            if request.status not in allowed_from[decision]:
                raise PaymentConflictError("Yêu cầu quyền lợi đã được xử lý.")
            before_status = request.status
            request.status = next_status
            request.decision_note = note
            request.reviewed_by_user_id = principal.user_id
            request.reviewed_at = datetime.now(UTC)
            await self.session.flush()
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action=f"membership.benefit_request.{decision.replace('-', '_')}",
                resource_type="membership_benefit_request",
                resource_id=str(identifier),
                before={"status": before_status},
                after={"benefit": request.benefit, "status": next_status},
            )
            await self.session.refresh(request)
            return request

    async def collaboration_needs(
        self, principal: AuthPrincipal
    ) -> list[dict[str, object]]:
        async with self.session.begin():
            tier, _ = await active_membership_cycle(self.session, principal.user_id)
            if TIERS.get(tier, -1) < TIERS["COMPANION"]:
                raise PaymentForbiddenError()
            if tier == "PRESTIGE":
                approved = await self.session.scalar(
                    select(MembershipDiamondApplication.id)
                    .where(
                        MembershipDiamondApplication.user_id == principal.user_id,
                        MembershipDiamondApplication.status == "APPROVED",
                    )
                    .limit(1)
                )
                if approved is None:
                    raise PaymentForbiddenError()
            rows = await self.session.execute(
                select(
                    MembershipBenefitRequest,
                    UserProfile.display_name,
                    CommunityProfile.username,
                )
                .outerjoin(
                    UserProfile,
                    UserProfile.user_id == MembershipBenefitRequest.user_id,
                )
                .outerjoin(
                    CommunityProfile,
                    CommunityProfile.user_id == MembershipBenefitRequest.user_id,
                )
                .where(
                    MembershipBenefitRequest.benefit == "COLLABORATION_NEED",
                    MembershipBenefitRequest.status == "APPROVED",
                )
                .order_by(MembershipBenefitRequest.created_at.desc())
                .limit(100)
            )
            return [
                {
                    "id": request.id,
                    "display_name": display_name or username or "Hội viên",
                    "username": username,
                    "statement": request.statement,
                    "created_at": request.created_at,
                }
                for request, display_name, username in rows.all()
            ]

    async def chat(
        self, principal: AuthPrincipal, room: str, body: str | None = None
    ) -> list[dict[str, object]]:
        async with self.session.begin():
            current = await self.current(principal.user_id)
            access_source = await self._chat_access_source(principal, room, current)
            if access_source == "NONE":
                raise PaymentForbiddenError()
            if body is not None:
                if not 1 <= len(body.strip()) <= 2000:
                    raise PaymentConflictError("Tin nhắn cần có từ 1 đến 2.000 ký tự.")
                await self.session.scalar(
                    select(User.id)
                    .where(User.id == principal.user_id)
                    .with_for_update()
                )
                now = datetime.now(UTC)
                restriction = await self.session.scalar(
                    select(CommunityMemberRestriction.id).where(
                        CommunityMemberRestriction.member_user_id == principal.user_id,
                        CommunityMemberRestriction.scope == "COMMENTS",
                        CommunityMemberRestriction.starts_at <= now,
                        CommunityMemberRestriction.expires_at > now,
                        CommunityMemberRestriction.revoked_at.is_(None),
                    )
                )
                if restriction is not None:
                    raise PaymentForbiddenError()
                latest = await self.session.scalar(
                    select(CommunityChatMessage.created_at)
                    .where(CommunityChatMessage.user_id == principal.user_id)
                    .order_by(CommunityChatMessage.created_at.desc())
                    .limit(1)
                )
                if latest is not None and now - utc(latest) < timedelta(seconds=2):
                    raise DomainError(
                        code="CHAT_RATE_LIMITED",
                        message="Vui lòng chờ một chút trước khi gửi tiếp.",
                        status_code=429,
                    )
                self.session.add(
                    CommunityChatMessage(
                        user_id=principal.user_id,
                        room=room,
                        body=body.strip(),
                        tier_snapshot=str(current["tier"]),
                    )
                )
                await self.session.flush()
            rows = await self.session.execute(
                select(
                    CommunityChatMessage,
                    CommunityProfile.display_name,
                    UserProfile.display_name,
                    CommunityProfile.avatar_url,
                    UserProfile.avatar_url,
                    UserProfile.avatar_media_id,
                    CommunityRepository._membership_tier(
                        CommunityChatMessage.user_id
                    ),
                    CommunityRepository._has_role(
                        CommunityChatMessage.user_id, "SUPER_ADMIN"
                    ),
                    CommunityRepository._has_role(
                        CommunityChatMessage.user_id, "MODERATOR"
                    ),
                )
                .outerjoin(
                    CommunityProfile,
                    CommunityProfile.user_id == CommunityChatMessage.user_id,
                )
                .outerjoin(
                    UserProfile,
                    UserProfile.user_id == CommunityChatMessage.user_id,
                )
                .where(
                    CommunityChatMessage.room == room,
                    CommunityChatMessage.deleted_at.is_(None),
                )
                .order_by(
                    CommunityChatMessage.created_at.desc(),
                    CommunityChatMessage.id.desc(),
                )
                .limit(50)
            )
            return [
                self._chat_message_data(principal, row)
                for row in reversed(rows.all())
            ]

    async def chat_access(
        self, principal: AuthPrincipal, room: str
    ) -> dict[str, object]:
        async with self.session.begin():
            current = await self.current(principal.user_id)
            source = await self._chat_access_source(principal, room, current)
            return {"room": room, "allowed": source != "NONE", "source": source}

    async def chat_access_candidates(
        self, principal: AuthPrincipal, query: str
    ) -> list[dict[str, object]]:
        self._require_membership_manager(principal)
        search = query.strip()
        if len(search) < 2:
            return []
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        async with self.session.begin():
            rows = await self.session.execute(
                select(User, UserProfile, CommunityProfile)
                .outerjoin(UserProfile, UserProfile.user_id == User.id)
                .outerjoin(CommunityProfile, CommunityProfile.user_id == User.id)
                .where(
                    User.status == UserStatus.ACTIVE,
                    User.disabled_at.is_(None),
                    User.deleted_at.is_(None),
                    or_(
                        User.email.ilike(pattern, escape="\\"),
                        UserProfile.display_name.ilike(pattern, escape="\\"),
                        UserProfile.full_name.ilike(pattern, escape="\\"),
                        CommunityProfile.display_name.ilike(pattern, escape="\\"),
                        CommunityProfile.username.ilike(pattern, escape="\\"),
                    ),
                )
                .order_by(User.email)
                .limit(20)
            )
            return [
                {
                    "user_id": user.id,
                    "email": user.email,
                    "display_name": self._membership_user_name(
                        user, profile, community
                    ),
                }
                for user, profile, community in rows.all()
            ]

    async def list_chat_room_access(
        self, principal: AuthPrincipal, room: str | None = None
    ) -> list[dict[str, object]]:
        self._require_membership_manager(principal)
        async with self.session.begin():
            statement = (
                select(MembershipChatRoomAccess, User, UserProfile, CommunityProfile)
                .join(User, User.id == MembershipChatRoomAccess.user_id)
                .outerjoin(UserProfile, UserProfile.user_id == User.id)
                .outerjoin(CommunityProfile, CommunityProfile.user_id == User.id)
                .where(MembershipChatRoomAccess.revoked_at.is_(None))
                .order_by(MembershipChatRoomAccess.granted_at.desc())
                .limit(200)
            )
            if room is not None:
                statement = statement.where(MembershipChatRoomAccess.room == room)
            rows = await self.session.execute(statement)
            return [
                self._chat_room_access_data(grant, user, profile, community)
                for grant, user, profile, community in rows.all()
            ]

    async def grant_chat_room_access(
        self,
        principal: AuthPrincipal,
        user_id: UUID,
        room: str,
        reason: str,
    ) -> dict[str, object]:
        self._require_membership_manager(principal)
        if room not in {"MEMBER", "COMPANION", "PRESTIGE"}:
            raise PaymentConflictError("Phòng hội viên không hợp lệ.")
        clean_reason = reason.strip()
        if not 3 <= len(clean_reason) <= 240:
            raise PaymentConflictError("Lý do cấp quyền cần từ 3 đến 240 ký tự.")
        async with self.session.begin():
            user = await self.session.scalar(
                select(User)
                .where(
                    User.id == user_id,
                    User.status == UserStatus.ACTIVE,
                    User.disabled_at.is_(None),
                    User.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if user is None:
                raise PaymentNotFoundError()
            grant = await self.session.get(
                MembershipChatRoomAccess, (user_id, room)
            )
            if grant is not None and grant.revoked_at is None:
                raise PaymentConflictError("Tài khoản đã có quyền vào phòng này.")
            before: dict[str, object] | None = (
                {"revoked_at": grant.revoked_at, "reason": grant.reason}
                if grant is not None
                else None
            )
            now = datetime.now(UTC)
            if grant is None:
                grant = MembershipChatRoomAccess(
                    user_id=user_id,
                    room=room,
                    granted_by_user_id=principal.user_id,
                    reason=clean_reason,
                    granted_at=now,
                )
                self.session.add(grant)
            else:
                grant.granted_by_user_id = principal.user_id
                grant.reason = clean_reason
                grant.granted_at = now
                grant.revoked_at = None
            await self.session.flush()
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action="membership.chat_access.granted",
                resource_type="membership_chat_room_access",
                resource_id=f"{user_id}:{room}",
                before=before,
                after={"room": room, "reason": clean_reason},
            )
            profile = await self.session.get(UserProfile, user_id)
            community = await self.session.get(CommunityProfile, user_id)
            return self._chat_room_access_data(grant, user, profile, community)

    async def revoke_chat_room_access(
        self,
        principal: AuthPrincipal,
        user_id: UUID,
        room: str,
        reason: str,
    ) -> dict[str, object]:
        self._require_membership_manager(principal)
        if not 3 <= len(reason.strip()) <= 240:
            raise PaymentConflictError("Lý do thu hồi cần từ 3 đến 240 ký tự.")
        async with self.session.begin():
            grant = await self.session.get(
                MembershipChatRoomAccess, (user_id, room), with_for_update=True
            )
            if grant is None or grant.revoked_at is not None:
                raise PaymentNotFoundError()
            grant.revoked_at = datetime.now(UTC)
            user = await self.session.get(User, user_id)
            if user is None:
                raise PaymentNotFoundError()
            profile = await self.session.get(UserProfile, user_id)
            community = await self.session.get(CommunityProfile, user_id)
            AuditService(self.session).record(
                actor_user_id=principal.user_id,
                action="membership.chat_access.revoked",
                resource_type="membership_chat_room_access",
                resource_id=f"{user_id}:{room}",
                before={"room": room, "grant_reason": grant.reason},
                after={"reason": reason.strip()},
            )
            return self._chat_room_access_data(grant, user, profile, community)

    async def _chat_access_source(
        self,
        principal: AuthPrincipal,
        room: str,
        current: dict[str, object] | None = None,
    ) -> str:
        if room not in {"MEMBER", "COMPANION", "PRESTIGE"}:
            return "NONE"
        if self._is_membership_manager(principal):
            return "ADMIN"
        membership = current or await self.current(principal.user_id)
        if TIERS.get(str(membership["tier"]), -1) >= TIERS[room]:
            return "TIER"
        grant = await self.session.get(
            MembershipChatRoomAccess, (principal.user_id, room)
        )
        return "MANUAL" if grant is not None and grant.revoked_at is None else "NONE"

    @staticmethod
    def _is_membership_manager(principal: AuthPrincipal) -> bool:
        return (
            "SUPER_ADMIN" in principal.roles
            or AuthorizationPolicy.allows_capability(
                principal, PolicyRequirement("memberships.manage")
            )
        )

    @classmethod
    def _require_membership_manager(cls, principal: AuthPrincipal) -> None:
        if not cls._is_membership_manager(principal):
            raise PaymentForbiddenError()

    @staticmethod
    def _membership_user_name(
        user: User,
        profile: UserProfile | None,
        community: CommunityProfile | None,
    ) -> str:
        return (
            (community.display_name if community else None)
            or (profile.display_name if profile else None)
            or (profile.full_name if profile else None)
            or user.email
        )

    @classmethod
    def _chat_room_access_data(
        cls,
        grant: MembershipChatRoomAccess,
        user: User,
        profile: UserProfile | None,
        community: CommunityProfile | None,
    ) -> dict[str, object]:
        return {
            "user_id": user.id,
            "room": grant.room,
            "email": user.email,
            "display_name": cls._membership_user_name(user, profile, community),
            "reason": grant.reason,
            "granted_at": grant.granted_at,
            "granted_by_user_id": grant.granted_by_user_id,
        }

    @staticmethod
    def _chat_message_data(
        principal: AuthPrincipal,
        row: Row[
            tuple[
                CommunityChatMessage,
                str | None,
                str | None,
                str | None,
                str | None,
                UUID | None,
                str,
                bool,
                bool,
            ]
        ],
    ) -> dict[str, object]:
        (
            item,
            community_name,
            profile_name,
            community_avatar,
            profile_avatar,
            avatar_media_id,
            current_tier,
            is_admin,
            is_moderator,
        ) = row
        identity = public_user_identity(
            display_name=profile_name or community_name,
            avatar_url=profile_avatar or community_avatar,
            avatar_media_id=avatar_media_id,
            is_admin=bool(is_admin),
            is_moderator=bool(is_moderator),
        )
        return {
            "id": item.id,
            "display_name": identity.display_name,
            "avatar_url": identity.avatar_url,
            "body": item.body,
            "tier": current_tier,
            "created_at": item.created_at,
            "can_remove": item.user_id == principal.user_id
            or AuthorizationPolicy.allows_capability(
                principal, PolicyRequirement("community.moderate")
            ),
        }
