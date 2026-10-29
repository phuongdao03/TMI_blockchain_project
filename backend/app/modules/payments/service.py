import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.session_service import AuthPrincipal
from app.modules.billing.models import FeeObligationStatus
from app.modules.billing.repository import BillingRepository
from app.modules.billing.service import FeeObligationView
from app.modules.dossiers.models import Dossier, DossierStatus, DossierStatusHistory
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.workflow import DossierWorkflowService
from app.modules.notifications.models import Notification
from app.modules.payments.errors import (
    PaymentAmountMismatchError,
    PaymentConflictError,
    PaymentForbiddenError,
    PaymentHistoryFilterError,
    PaymentInvalidWebhookError,
    PaymentNotFoundError,
    PaymentProviderError,
)
from app.modules.payments.gateway import (
    InvalidWebhookError,
    PaymentGateway,
    PaymentGatewayError,
    ProviderOrder,
)
from app.modules.payments.models import (
    PaymentEvent,
    PaymentOrder,
    PaymentStatus,
    PaymentStatusHistory,
)
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.types import (
    AdminPaymentHistoryDetailView,
    AdminPaymentHistoryPageView,
    AdminPaymentHistoryRowView,
    AdminPaymentHistorySummaryView,
    AdminPaymentOrderView,
    PaymentCandidateView,
    PaymentOrderView,
    PaymentStatusHistoryView,
    PaymentWaiverView,
)
from app.modules.wallet.service import WalletLedger, WalletService, valid_key

logger = logging.getLogger(__name__)

PAYMENT_ROLES = frozenset({"USER"})
FINANCE_ROLES = frozenset({"SUPER_ADMIN"})
RECONCILIATION_REQUIREMENT = PolicyRequirement(
    permission="payments.reconcile",
    compatible_roles=FINANCE_ROLES,
)
PAYMENT_HISTORY_READ_REQUIREMENT = PolicyRequirement(
    permission="payments.read",
    compatible_roles=FINANCE_ROLES,
)
PAYMENT_HISTORY_EXPORT_REQUIREMENT = PolicyRequirement(
    permission="payments.export",
    compatible_roles=FINANCE_ROLES,
)
ISSUE_PAYMENT_REQUIREMENT = PolicyRequirement(permission="payments.issue")
PAYMENT_REQUIREMENTS = {
    PAYMENT_ROLES: PolicyRequirement(
        permission="payment.create",
        compatible_roles=PAYMENT_ROLES,
        allow_super_admin=False,
    ),
    FINANCE_ROLES: PolicyRequirement(
        permission="payment.manage", compatible_roles=FINANCE_ROLES
    ),
}


class PaymentService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: PaymentGateway,
        provider_name: str,
        amount_minor: int,
        currency: str,
        order_ttl_seconds: int,
        enqueue_certificate_issue: Callable[[UUID], None] | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        if amount_minor <= 0:
            raise ValueError("Payment amount must be positive.")
        if len(currency) != 3:
            raise ValueError("Payment currency must be a three-letter code.")
        self._session = session
        self._gateway = gateway
        self._provider_name = provider_name
        self._amount_minor = amount_minor
        self._currency = currency.upper()
        self._order_ttl = timedelta(seconds=order_ttl_seconds)
        self._enqueue_certificate_issue = enqueue_certificate_issue
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._payments = PaymentRepository(session)
        self._auth = AuthRepository(session)
        self._billing = BillingRepository(session)
        self._audit_service = AuditService(session)
        self._dossiers = DossierRepository(session)
        self._workflow = DossierWorkflowService(self._dossiers)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def wallet_service(self) -> WalletService:
        return WalletService(
            session=self._session,
            gateway=self._gateway,
            provider=self._provider_name,
            ttl_seconds=int(self._order_ttl.total_seconds()),
        )

    async def pay_with_wallet(
        self, principal: AuthPrincipal, order_id: UUID, *, idempotency_key: str
    ) -> PaymentOrderView:
        key = valid_key(idempotency_key)
        self._require_role(principal, PAYMENT_ROLES)
        newly_paid = False
        async with self._session.begin():
            order = await self._required_order(order_id, for_update=True)
            dossier = await self._required_dossier(order.dossier_id, for_update=True)
            # Wallet spending is always by the owner, never staff on their behalf.
            if dossier.owner_user_id != principal.user_id:
                raise PaymentForbiddenError()
            if order.status is PaymentStatus.PAID:
                if (
                    order.provider != "wallet"
                    or order.metadata_json.get("wallet_key") != key
                ):
                    raise PaymentConflictError("Khoản thu đã được thanh toán.")
                return self._view(order)
            if order.status is not PaymentStatus.PENDING or order.currency != "VND":
                raise PaymentConflictError("Khoản thu chưa thể thanh toán bằng ví.")
            if order.provider_order_id is not None:
                raise PaymentConflictError(
                    "Khoản thu đã mở cổng thanh toán. "
                    "Vui lòng hoàn tất hoặc hủy giao dịch đó trước."
                )
            if self._utc(order.expires_at) <= self._clock():
                raise PaymentConflictError("Yêu cầu thanh toán đã hết hạn.")
            if order.amount_minor > 0:
                await WalletLedger(self._session).post(
                    user_id=principal.user_id,
                    delta=-order.amount_minor,
                    kind="PAYMENT",
                    key=key,
                    reference=f"payment:{order.id}",
                    description=str(
                        order.metadata_json.get("description") or "Phí xác lập hồ sơ"
                    ),
                )
            self._workflow.transition(
                dossier,
                target=self._confirmed_dossier_status(dossier),
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.PAYMENT_PENDING},
                reason_code="WALLET_PAYMENT_CONFIRMED",
            )
            order.provider = "wallet"
            order.metadata_json = {**order.metadata_json, "wallet_key": key}
            order.paid_at = self._clock()
            self._transition_status(
                order, PaymentStatus.PAID, source="WALLET", actor=principal.user_id
            )
            await self._settle_fee_obligation(order)
            await self._add_paid_notification(
                dossier, order, source_event_id=uuid5(order.id, "wallet-paid")
            )
            self._audit(
                "payment.wallet.confirmed",
                order.id,
                user_id=principal.user_id,
                status=order.status,
            )
            await self._session.flush()
            await self._session.refresh(order)
            result = self._view(order)
            newly_paid = not dossier.submission_fee_required
        if newly_paid and self._enqueue_certificate_issue is not None:
            self._enqueue_certificate_issue(result.dossier_id)
        return result

    async def _ensure_checkout(
        self, order_id: UUID, *, newly_reserved: bool = False
    ) -> PaymentOrderView:
        """Resolve a durable reservation using the same provider order code."""
        async with self._session.begin():
            order = await self._required_order(order_id, for_update=True)
            if order.provider == "wallet":
                return self._view(order)
            if (
                order.provider_order_id is not None
                or order.status is PaymentStatus.PAID
            ):
                return self._view(order)
            if order.status not in {PaymentStatus.PENDING, PaymentStatus.PROCESSING}:
                raise PaymentConflictError("This payment request is no longer active.")
            if order.status is PaymentStatus.PENDING:
                self._transition_status(
                    order, PaymentStatus.PROCESSING, source="CHECKOUT_RESERVED"
                )
                order.metadata_json = {
                    **order.metadata_json,
                    "checkout_requested_at": self._clock().isoformat(),
                }
            order_code = order.order_code
            amount_minor = order.amount_minor
            currency = order.currency
            expires_at = order.expires_at
        provider_order: ProviderOrder | None = None
        if not newly_reserved:
            try:
                provider_order = await self._gateway.get_order(order_code)
            except PaymentGatewayError:
                pass
        if provider_order is None:
            try:
                provider_order = await self._gateway.create_order(
                    order_code=order_code,
                    amount_minor=amount_minor,
                    currency=currency,
                    expires_at=expires_at,
                )
            except PaymentGatewayError as exc:
                # The reservation remains reconcilable after a timeout or restart.
                raise PaymentProviderError() from exc
        if (
            provider_order.order_code not in {None, order_code}
            or provider_order.amount_minor not in {None, amount_minor}
            or provider_order.currency not in {None, currency}
        ):
            raise PaymentAmountMismatchError()
        async with self._session.begin():
            order = await self._required_order(order_id, for_update=True)
            if order.provider == "wallet" or order.status in {
                PaymentStatus.CANCELLED,
                PaymentStatus.EXPIRED,
                PaymentStatus.REFUNDED,
            }:
                raise PaymentConflictError("Payment state changed during checkout.")
            if order.provider_order_id not in {None, provider_order.provider_order_id}:
                raise PaymentConflictError("Provider order changed during checkout.")
            order.provider_order_id = provider_order.provider_order_id
            if order.status is PaymentStatus.PROCESSING:
                self._transition_status(
                    order, PaymentStatus.PENDING, source="CHECKOUT_READY"
                )
            order.metadata_json = {
                **order.metadata_json,
                "checkout_url": provider_order.checkout_url,
                "qr_payload": provider_order.qr_payload,
                "bank_bin": provider_order.bank_bin,
                "bank_account_number": provider_order.bank_account_number,
                "bank_account_name": provider_order.bank_account_name,
                "transfer_description": provider_order.transfer_description,
            }
            await self._session.flush()
            await self._session.refresh(order)
            return self._view(order)

    async def create_order(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
    ) -> PaymentOrderView:
        self._require_role(principal, PAYMENT_ROLES)
        normalized_key = idempotency_key.strip()
        if not normalized_key or len(normalized_key) > 128:
            raise PaymentConflictError("Idempotency key is invalid.")
        replay_id: UUID | None = None
        async with self._session.begin():
            replay = await self._payments.get_by_idempotency(normalized_key)
            if replay is not None:
                dossier = await self._required_dossier(replay.dossier_id)
                await self._require_access(principal, dossier)
                if replay.dossier_id != dossier_id:
                    raise PaymentConflictError("Idempotency key is already in use.")
                replay_id = replay.id
            else:
                dossier = await self._required_dossier(dossier_id, for_update=True)
                await self._require_access(principal, dossier)
                if (
                    dossier.submission_fee_required
                    or dossier.status is not DossierStatus.APPROVED
                ):
                    raise PaymentConflictError(
                        "Only an approved dossier can create a payment order."
                    )
                if await self._payments.get_active_for_dossier(dossier.id):
                    raise PaymentConflictError(
                        "This dossier already has an active payment order."
                    )
                order_id = self._uuid_factory()
                order_code = str((order_id.int % 2_147_483_646) + 1)
                expires_at = self._clock() + self._order_ttl
                order = PaymentOrder(
                    id=order_id,
                    order_code=order_code,
                    dossier_id=dossier.id,
                    initiated_by_user_id=principal.user_id,
                    provider=self._provider_name,
                    amount_minor=self._amount_minor,
                    currency=self._currency,
                    status=PaymentStatus.PROCESSING,
                    expires_at=expires_at,
                    idempotency_key=normalized_key,
                    metadata_json={},
                )
                self._payments.add_order(order)
                self._record_initial_status(
                    order, source="ORDER_CREATED", actor=principal.user_id
                )
                self._workflow.transition(
                    dossier,
                    target=DossierStatus.PAYMENT_PENDING,
                    actor_user_id=principal.user_id,
                    allowed_sources={DossierStatus.APPROVED},
                    reason_code="PAYMENT_ORDER_CREATED",
                )
                self._audit(
                    "payment.order.created",
                    order_id,
                    user_id=principal.user_id,
                    status=PaymentStatus.PROCESSING,
                )
                await self._session.flush()
        return await self._ensure_checkout(
            replay_id or order_id, newly_reserved=replay_id is None
        )

    async def create_checkout_for_obligation(
        self,
        principal: AuthPrincipal,
        obligation_id: UUID,
        *,
        idempotency_key: str,
    ) -> PaymentOrderView:
        self._require_role(principal, PAYMENT_ROLES)
        normalized_key = idempotency_key.strip()
        if not normalized_key or len(normalized_key) > 128:
            raise PaymentConflictError("Idempotency key is invalid.")
        result: PaymentOrderView | None = None
        replay_id: UUID | None = None
        async with self._session.begin():
            replay = await self._payments.get_by_idempotency(normalized_key)
            if replay is not None:
                if replay.fee_obligation_id != obligation_id:
                    raise PaymentConflictError("Idempotency key is already in use.")
                dossier = await self._required_dossier(replay.dossier_id)
                await self._require_access(principal, dossier)
                replay_id = replay.id
        if replay_id is not None:
            async with self._session.begin():
                return self._view(await self._required_order(replay_id))
        expired_order_id: UUID | None = None
        async with self._session.begin():
            obligation = await self._billing.obligation_by_id(obligation_id)
            if obligation is None:
                raise PaymentNotFoundError("Fee obligation was not found.")
            dossier = await self._required_dossier(obligation.dossier_id)
            await self._require_access(principal, dossier)
            if obligation.owner_user_id != principal.user_id:
                raise PaymentForbiddenError()
            active = await self._payments.get_active_for_obligation(obligation_id)
            if active is not None and self._utc(active.expires_at) <= self._clock():
                expired_order_id = active.id
        if expired_order_id is not None:
            async with self._session.begin():
                expired_order = await self._required_order(
                    expired_order_id, for_update=True
                )
                await self._expire_if_needed(expired_order)
        async with self._session.begin():
            obligation = await self._billing.obligation_by_id(
                obligation_id, for_update=True
            )
            if obligation is None:
                raise PaymentNotFoundError("Fee obligation was not found.")
            dossier = await self._required_dossier(
                obligation.dossier_id, for_update=True
            )
            await self._require_access(principal, dossier)
            if obligation.owner_user_id != principal.user_id:
                raise PaymentForbiddenError()
            if obligation.status not in {
                FeeObligationStatus.OPEN,
                FeeObligationStatus.OVERDUE,
            }:
                raise PaymentConflictError("Fee obligation is not payable.")
            if dossier.status is not DossierStatus.PAYMENT_PENDING:
                raise PaymentConflictError("Dossier is not awaiting payment.")
            active = await self._payments.get_active_for_obligation(obligation.id)
            if active is not None:
                await self._expire_if_needed(active)
                if active.status in {
                    PaymentStatus.PENDING,
                    PaymentStatus.PROCESSING,
                }:
                    result = self._view(active)
                if result is None:
                    raise PaymentConflictError(
                        "Checkout expiry needs reconciliation; please retry."
                    )
            if result is None:
                order_id = self._uuid_factory()
                order_code = str((order_id.int % 2_147_483_646) + 1)
                due_at = obligation.due_at
                if due_at.tzinfo is None:
                    due_at = due_at.replace(tzinfo=UTC)
                expires_at = max(self._clock() + self._order_ttl, due_at)
                order = PaymentOrder(
                    id=order_id,
                    order_code=order_code,
                    dossier_id=dossier.id,
                    initiated_by_user_id=principal.user_id,
                    fee_obligation_id=obligation.id,
                    provider="wallet",
                    amount_minor=obligation.amount_minor,
                    currency=obligation.currency,
                    status=PaymentStatus.PENDING,
                    expires_at=expires_at,
                    idempotency_key=normalized_key,
                    metadata_json={
                        "description": obligation.description,
                        "due_at": obligation.due_at.isoformat(),
                    },
                )
                self._payments.add_order(order)
                self._record_initial_status(
                    order, source="WALLET_PAYMENT_REQUESTED", actor=principal.user_id
                )
                self._audit(
                    "payment.wallet.requested",
                    order.id,
                    user_id=principal.user_id,
                    status=PaymentStatus.PENDING,
                )
                await self._session.flush()
                result = self._view(order)
            await self._session.flush()
        if result is None:
            raise RuntimeError("Payment checkout did not produce a result.")
        return result

    async def issue_order(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
        amount_minor: int,
        currency: str,
        description: str,
        due_at: datetime | None,
    ) -> PaymentOrderView:
        AuthorizationPolicy.require_capability(
            principal,
            ISSUE_PAYMENT_REQUIREMENT,
            PaymentForbiddenError,
        )
        normalized_key = idempotency_key.strip()
        normalized_currency = currency.strip().upper()
        normalized_description = description.strip()
        now = self._clock()
        if not normalized_key or len(normalized_key) > 128:
            raise PaymentConflictError("Idempotency key is invalid.")
        if amount_minor < 1_000 or amount_minor > 1_000_000_000:
            raise PaymentConflictError("Payment amount is outside the allowed range.")
        if normalized_currency != "VND":
            raise PaymentConflictError("Only VND payment requests are supported.")
        if not 5 <= len(normalized_description) <= 255:
            raise PaymentConflictError("Payment description is invalid.")
        if due_at is not None:
            normalized_due_at = due_at if due_at.tzinfo else due_at.replace(tzinfo=UTC)
            if normalized_due_at <= now or normalized_due_at > now + timedelta(days=30):
                raise PaymentConflictError("Payment due time is invalid.")
        else:
            normalized_due_at = None

        replay_id: UUID | None = None
        newly_paid = False
        async with self._session.begin():
            replay = await self._payments.get_by_idempotency(normalized_key)
            if replay is not None:
                if (
                    replay.dossier_id != dossier_id
                    or replay.fee_obligation_id is not None
                    or replay.amount_minor != amount_minor
                    or replay.currency != normalized_currency
                    or replay.metadata_json.get("description") != normalized_description
                    or replay.metadata_json.get("due_at")
                    != (normalized_due_at.isoformat() if normalized_due_at else None)
                ):
                    raise PaymentConflictError("Idempotency key is already in use.")
                replay_id = replay.id
        if replay_id is not None:
            async with self._session.begin():
                return self._view(await self._required_order(replay_id))
        async with self._session.begin():
            dossier = await self._required_dossier(dossier_id, for_update=True)
            if (
                dossier.submission_fee_required
                or dossier.status is not DossierStatus.APPROVED
            ):
                raise PaymentConflictError(
                    "Only an approved dossier can receive a payment request."
                )
            if await self._payments.get_active_for_dossier(dossier.id):
                raise PaymentConflictError(
                    "This dossier already has an active payment request."
                )
            order_id = self._uuid_factory()
            order_code = str((order_id.int % 2_147_483_646) + 1)
            request_expires_at = normalized_due_at or now + timedelta(days=30)
            order = PaymentOrder(
                id=order_id,
                order_code=order_code,
                dossier_id=dossier.id,
                initiated_by_user_id=principal.user_id,
                provider="wallet",
                amount_minor=amount_minor,
                currency=normalized_currency,
                status=PaymentStatus.PENDING,
                expires_at=request_expires_at,
                idempotency_key=normalized_key,
                metadata_json={
                    "description": normalized_description,
                    "due_at": normalized_due_at.isoformat()
                    if normalized_due_at
                    else None,
                    "issued_by_user_id": str(principal.user_id),
                    "issued_at": now.isoformat(),
                },
            )
            self._payments.add_order(order)
            self._record_initial_status(
                order, source="REQUEST_ISSUED", actor=principal.user_id
            )
            self._workflow.transition(
                dossier,
                target=DossierStatus.PAYMENT_PENDING,
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.APPROVED},
                reason_code="PAYMENT_REQUEST_ISSUED",
                note=normalized_description,
            )
            wallet_key = f"admin-fee:{order_id}"
            try:
                await WalletLedger(self._session).post(
                    user_id=dossier.owner_user_id,
                    delta=-amount_minor,
                    kind="PAYMENT",
                    key=wallet_key,
                    reference=f"payment:{order_id}",
                    description=normalized_description,
                )
            except DomainError as exc:
                if exc.code != "WALLET_INSUFFICIENT_FUNDS":
                    raise
                self._session.add(
                    Notification(
                        user_id=dossier.owner_user_id,
                        source_event_id=order_id,
                        type="PAYMENT_REQUEST_ISSUED",
                        title="Hồ sơ có yêu cầu thanh toán",
                        body=(
                            f"Số tiền cần thanh toán: {amount_minor:,} VND. "
                            "Số dư ví chưa đủ; vui lòng nạp thêm để hoàn tất."
                        ),
                        data_json={
                            "dossierId": str(dossier.id),
                            "paymentOrderId": str(order_id),
                            "actionPath": f"/payments/{order_id}",
                        },
                        created_at=now,
                    )
                )
            else:
                self._workflow.transition(
                    dossier,
                    target=self._confirmed_dossier_status(dossier),
                    actor_user_id=principal.user_id,
                    allowed_sources={DossierStatus.PAYMENT_PENDING},
                    reason_code="ADMIN_FEE_WALLET_PAYMENT",
                    note=normalized_description,
                )
                order.metadata_json = {**order.metadata_json, "wallet_key": wallet_key}
                order.paid_at = now
                self._transition_status(
                    order,
                    PaymentStatus.PAID,
                    source="WALLET",
                    actor=principal.user_id,
                )
                await self._settle_fee_obligation(order)
                await self._add_paid_notification(
                    dossier, order, source_event_id=uuid5(order.id, "wallet-paid")
                )
                self._audit(
                    "payment.wallet.confirmed",
                    order.id,
                    user_id=principal.user_id,
                    status=order.status,
                )
                newly_paid = not dossier.submission_fee_required
            self._audit(
                "payment.request.issued",
                order_id,
                user_id=principal.user_id,
                status=order.status,
                reason=normalized_description,
            )
            await self._session.flush()
            await self._session.refresh(order)
            result = self._view(order)
        if newly_paid and self._enqueue_certificate_issue is not None:
            self._enqueue_certificate_issue(result.dossier_id)
        return result

    async def start_order_checkout(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
    ) -> PaymentOrderView:
        """Create the provider checkout only after the dossier owner starts payment."""
        self._require_role(principal, PAYMENT_ROLES)
        newly_started = False
        expired = False
        zero_checkout = False
        result: PaymentOrderView | None = None
        async with self._session.begin():
            order = await self._required_order(order_id, for_update=True)
            dossier = await self._required_dossier(order.dossier_id)
            await self._require_access(principal, dossier)
            if order.provider == "wallet":
                raise PaymentConflictError(
                    "This payment request uses the personal wallet."
                )
            await self._expire_if_needed(order)
            if order.status is PaymentStatus.EXPIRED:
                expired = True
            elif (
                order.provider_order_id is not None
                or order.status is PaymentStatus.PAID
            ):
                result = self._view(order)
            elif order.amount_minor == 0 and order.status is PaymentStatus.PENDING:
                zero_checkout = True
            elif order.status not in {
                PaymentStatus.PENDING,
                PaymentStatus.PROCESSING,
            }:
                raise PaymentConflictError("This payment request is no longer active.")
            else:
                if order.status is PaymentStatus.PENDING:
                    due_at = self._metadata_datetime(order.metadata_json.get("due_at"))
                    if due_at is not None:
                        due_at = self._utc(due_at)
                    provider_expires_at = self._clock() + self._order_ttl
                    order.expires_at = (
                        min(provider_expires_at, due_at)
                        if due_at is not None
                        else provider_expires_at
                    )
                    self._transition_status(
                        order,
                        PaymentStatus.PROCESSING,
                        source="CHECKOUT_REQUESTED",
                        actor=principal.user_id,
                    )
                    order.metadata_json = {
                        **order.metadata_json,
                        "checkout_requested_at": self._clock().isoformat(),
                    }
                    self._audit(
                        "payment.checkout.started",
                        order.id,
                        user_id=principal.user_id,
                        status=order.status,
                    )
                    newly_started = True
                await self._session.flush()
        if expired:
            raise PaymentConflictError("This payment request has expired.")
        if result is not None:
            return result
        if zero_checkout:
            return await self.pay_with_wallet(principal, order_id, idempotency_key=f"promotion-zero-{order_id}")
        return await self._ensure_checkout(
            order_id,
            newly_reserved=newly_started,
        )

    async def list_payment_candidates(
        self,
        principal: AuthPrincipal,
    ) -> tuple[PaymentCandidateView, ...]:
        AuthorizationPolicy.require_capability(
            principal,
            ISSUE_PAYMENT_REQUIREMENT,
            PaymentForbiddenError,
        )
        async with self._session.begin():
            dossiers = tuple(
                (
                    await self._session.scalars(
                        select(Dossier)
                        .where(
                            Dossier.status == DossierStatus.APPROVED,
                            Dossier.deleted_at.is_(None),
                        )
                        .order_by(Dossier.updated_at.desc(), Dossier.id.desc())
                        .limit(100)
                    )
                ).all()
            )
            return tuple(
                PaymentCandidateView(
                    dossier_id=dossier.id,
                    dossier_code=dossier.code,
                    dossier_title=dossier.title,
                    version_no=dossier.current_version_no,
                )
                for dossier in dossiers
            )

    async def list_admin_orders(
        self,
        principal: AuthPrincipal,
        *,
        status: PaymentStatus | None,
        limit: int = 50,
    ) -> tuple[AdminPaymentOrderView, ...]:
        AuthorizationPolicy.require_capability(
            principal, PAYMENT_HISTORY_READ_REQUIREMENT, PaymentForbiddenError
        )
        if not 1 <= limit <= 100:
            raise ValueError("Payment order list limit is invalid.")
        async with self._session.begin():
            rows = await self._payments.list_for_admin(status=status, limit=limit)
        return tuple(
            AdminPaymentOrderView(
                order=self._view(order),
                dossier_code=dossier_code,
                dossier_title=dossier_title,
            )
            for order, dossier_code, dossier_title in rows
        )

    async def list_admin_history(
        self,
        principal: AuthPrincipal,
        *,
        status: PaymentStatus | None,
        created_from: datetime | None,
        created_to: datetime | None,
        query: str | None,
        page: int,
        page_size: int,
    ) -> tuple[AdminPaymentHistoryPageView, int]:
        AuthorizationPolicy.require_capability(
            principal, PAYMENT_HISTORY_READ_REQUIREMENT, PaymentForbiddenError
        )
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("Payment history pagination is invalid.")
        created_from, created_to, normalized_query = self._normalize_history_filters(
            created_from, created_to, query
        )
        async with self._session.begin():
            (
                rows,
                total,
                counts,
                total_amount,
                paid_amount,
            ) = await self._payments.list_history_for_admin(
                status=status,
                created_from=created_from,
                created_to=created_to,
                query=normalized_query,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        return (
            AdminPaymentHistoryPageView(
                rows=tuple(self._history_row(row) for row in rows),
                summary=AdminPaymentHistorySummaryView(
                    total=total,
                    status_counts=counts,
                    total_amount_minor=total_amount,
                    paid_amount_minor=paid_amount,
                ),
            ),
            total,
        )

    async def get_admin_history_detail(
        self, principal: AuthPrincipal, order_id: UUID
    ) -> AdminPaymentHistoryDetailView:
        AuthorizationPolicy.require_capability(
            principal, PAYMENT_HISTORY_READ_REQUIREMENT, PaymentForbiddenError
        )
        async with self._session.begin():
            row, history = await self._payments.get_history_detail_for_admin(order_id)
        if row is None:
            raise PaymentNotFoundError()
        return AdminPaymentHistoryDetailView(
            row=self._history_row(row),
            status_history=tuple(
                PaymentStatusHistoryView(
                    id=item.id,
                    from_status=item.from_status,
                    to_status=item.to_status,
                    source=item.source,
                    actor_user_id=item.actor_user_id,
                    actor_email=actor_email,
                    changed_at=self._utc(item.changed_at),
                )
                for item, actor_email in history
            ),
        )

    async def export_admin_history(
        self,
        principal: AuthPrincipal,
        *,
        status: PaymentStatus | None,
        created_from: datetime | None,
        created_to: datetime | None,
        query: str | None,
    ) -> tuple[AdminPaymentHistoryRowView, ...]:
        AuthorizationPolicy.require_capability(
            principal, PAYMENT_HISTORY_EXPORT_REQUIREMENT, PaymentForbiddenError
        )
        created_from, created_to, normalized_query = self._normalize_history_filters(
            created_from, created_to, query
        )
        async with self._session.begin():
            rows, _, _, _, _ = await self._payments.list_history_for_admin(
                status=status,
                created_from=created_from,
                created_to=created_to,
                query=normalized_query,
                limit=None,
            )
        return tuple(self._history_row(row) for row in rows)

    @staticmethod
    def _history_row(row: tuple[Any, ...]) -> AdminPaymentHistoryRowView:
        order, code, title, applicant_id, applicant_email, initiator_email = row
        return AdminPaymentHistoryRowView(
            order=PaymentService._view(order),
            dossier_code=code,
            dossier_title=title,
            applicant_user_id=applicant_id,
            applicant_email=applicant_email,
            initiated_by_email=initiator_email,
        )

    @staticmethod
    def _normalize_history_filters(
        created_from: datetime | None,
        created_to: datetime | None,
        query: str | None,
    ) -> tuple[datetime | None, datetime | None, str | None]:
        if created_from is not None:
            created_from = PaymentService._utc(created_from)
        if created_to is not None:
            created_to = PaymentService._utc(created_to)
        if (
            created_from is not None
            and created_to is not None
            and created_from > created_to
        ):
            raise PaymentHistoryFilterError("Payment history date range is invalid.")
        normalized = query.strip() if query else None
        if normalized is not None and len(normalized) > 120:
            raise PaymentHistoryFilterError("Payment history search is too long.")
        return created_from, created_to, normalized or None

    async def waive_payment(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
        reason: str,
    ) -> PaymentWaiverView:
        AuthorizationPolicy.require_capability(
            principal,
            ISSUE_PAYMENT_REQUIREMENT,
            PaymentForbiddenError,
        )
        normalized_key = idempotency_key.strip()
        normalized_reason = reason.strip()
        if not normalized_key or len(normalized_key) > 128:
            raise PaymentConflictError("Idempotency key is invalid.")
        if not 5 <= len(normalized_reason) <= 500:
            raise PaymentConflictError("Payment waiver reason is invalid.")

        should_issue = False
        async with self._session.begin():
            dossier = await self._required_dossier(dossier_id, for_update=True)
            prior_waiver = await self._session.scalar(
                select(DossierStatusHistory).where(
                    DossierStatusHistory.dossier_id == dossier.id,
                    DossierStatusHistory.reason_code == "PAYMENT_WAIVED",
                )
            )
            if prior_waiver is not None and dossier.status in {
                DossierStatus.PAID,
                DossierStatus.ANCHOR_PENDING,
                DossierStatus.ANCHORED,
                DossierStatus.CERTIFICATE_ISSUED,
                DossierStatus.PUBLISHED,
            }:
                return PaymentWaiverView(
                    dossier_id=dossier.id,
                    status=dossier.status,
                    reason=prior_waiver.note or normalized_reason,
                )
            if (
                dossier.submission_fee_required
                or dossier.status is not DossierStatus.APPROVED
            ):
                raise PaymentConflictError(
                    "Only an approved dossier can have its payment waived."
                )
            if await self._payments.get_active_for_dossier(dossier.id):
                raise PaymentConflictError(
                    "This dossier already has an active payment request."
                )

            self._workflow.transition(
                dossier,
                target=self._confirmed_dossier_status(dossier),
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.APPROVED},
                reason_code="PAYMENT_WAIVED",
                note=normalized_reason,
            )
            now = self._clock()
            self._session.add(
                Notification(
                    user_id=dossier.owner_user_id,
                    source_event_id=uuid5(dossier.id, "payment-waived-owner"),
                    type="PAYMENT_WAIVED",
                    title="Hồ sơ được miễn phí",
                    body=(
                        "Hồ sơ không cần thanh toán và đã được chuyển sang "
                        "bước ký blockchain."
                    ),
                    data_json={
                        "dossierId": str(dossier.id),
                        "actionPath": f"/dossiers/{dossier.id}",
                    },
                    created_at=now,
                )
            )
            await self._add_admin_ready_notifications(
                dossier,
                source_event_id=uuid5(dossier.id, "payment-waived-admin"),
                body="Hồ sơ đã được miễn phí và sẵn sàng để ký blockchain.",
            )
            self._audit(
                "payment.waiver.issued",
                dossier.id,
                user_id=principal.user_id,
                reason=normalized_reason,
            )
            await self._session.flush()
            result = PaymentWaiverView(
                dossier_id=dossier.id,
                status=dossier.status,
                reason=normalized_reason,
            )
            should_issue = not dossier.submission_fee_required
        if should_issue and self._enqueue_certificate_issue is not None:
            self._enqueue_certificate_issue(dossier_id)
        return result

    async def get_order(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
    ) -> PaymentOrderView:
        async with self._session.begin():
            order = await self._required_order(order_id)
            dossier = await self._required_dossier(order.dossier_id)
            await self._require_access(principal, dossier)
            await self._expire_if_needed(order)
            result = self._view(order)
        return result

    async def get_order_by_provider_reference(
        self,
        principal: AuthPrincipal,
        provider_order_id: str,
    ) -> PaymentOrderView:
        normalized_id = provider_order_id.strip()
        if not normalized_id or len(normalized_id) > 128:
            raise PaymentNotFoundError()
        async with self._session.begin():
            order = await self._payments.get_by_provider_order(
                self._provider_name,
                normalized_id,
            )
            if order is None:
                raise PaymentNotFoundError()
            dossier = await self._required_dossier(order.dossier_id)
            await self._require_access(principal, dossier)
            await self._expire_if_needed(order)
            return self._view(order)

    async def get_active_order_for_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> PaymentOrderView:
        async with self._session.begin():
            dossier = await self._required_dossier(dossier_id)
            await self._require_access(principal, dossier)
            order = await self._payments.get_active_for_dossier(dossier_id)
            if order is None:
                raise PaymentNotFoundError()
            await self._expire_if_needed(order)
            return self._view(order)

    async def cancel_order(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
        *,
        reason: str,
    ) -> PaymentOrderView:
        self._require_role(principal, PAYMENT_ROLES)
        normalized_reason = reason.strip()
        if len(normalized_reason) < 5 or len(normalized_reason) > 500:
            raise PaymentConflictError("Payment cancellation reason is invalid.")
        async with self._session.begin():
            order = await self._required_order(order_id)
            dossier = await self._required_dossier(order.dossier_id)
            await self._require_access(principal, dossier)
            if order.status is PaymentStatus.CANCELLED:
                return self._view(order)
            if order.status not in {
                PaymentStatus.PENDING,
                PaymentStatus.PROCESSING,
            }:
                raise PaymentConflictError(
                    "Only an unpaid payment order can be cancelled."
                )
            if order.provider_order_id is None:
                if order.status is PaymentStatus.PROCESSING:
                    raise PaymentConflictError(
                        "Checkout session is still being initialized."
                    )
                dossier = await self._required_dossier(
                    order.dossier_id,
                    for_update=True,
                )
                self._workflow.transition(
                    dossier,
                    target=(
                        DossierStatus.PAYMENT_PENDING
                        if dossier.submission_fee_required
                        else DossierStatus.APPROVED
                    ),
                    actor_user_id=principal.user_id,
                    allowed_sources={DossierStatus.PAYMENT_PENDING},
                    reason_code="PAYMENT_ORDER_CANCELLED",
                    note=normalized_reason,
                )
                self._transition_status(
                    order,
                    PaymentStatus.CANCELLED,
                    source="CANCELLED_BY_USER",
                    actor=principal.user_id,
                )
                await self._release_voucher(order, normalized_reason)
                order.metadata_json = {
                    **order.metadata_json,
                    "cancellation_reason": normalized_reason,
                }
                await self._session.flush()
                await self._session.refresh(order)
                result = self._view(order)
                self._audit(
                    "payment.order.cancelled",
                    result.id,
                    user_id=principal.user_id,
                    status=result.status,
                    reason=normalized_reason,
                )
                return result
            provider_order_id = order.provider_order_id
        try:
            provider_order = await self._gateway.cancel_order(
                provider_order_id,
                reason=normalized_reason,
            )
        except PaymentGatewayError as exc:
            raise PaymentProviderError() from exc
        if provider_order.status != PaymentStatus.CANCELLED.value:
            raise PaymentProviderError("Provider did not cancel the order.")
        async with self._session.begin():
            order = await self._required_order(order_id, for_update=True)
            if order.status is PaymentStatus.PAID:
                return self._view(order)
            if order.status is PaymentStatus.CANCELLED:
                return self._view(order)
            if order.provider_order_id != provider_order_id or order.status not in {
                PaymentStatus.PENDING,
                PaymentStatus.PROCESSING,
            }:
                raise PaymentConflictError("Payment order changed during cancellation.")
            dossier = await self._required_dossier(order.dossier_id, for_update=True)
            self._workflow.transition(
                dossier,
                target=(
                    DossierStatus.PAYMENT_PENDING
                    if dossier.submission_fee_required
                    else DossierStatus.APPROVED
                ),
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.PAYMENT_PENDING},
                reason_code="PAYMENT_ORDER_CANCELLED",
                note=normalized_reason,
            )
            self._transition_status(
                order,
                PaymentStatus.CANCELLED,
                source="CANCELLED_BY_USER",
                actor=principal.user_id,
            )
            await self._release_voucher(order, normalized_reason)
            order.metadata_json = {
                **order.metadata_json,
                "cancellation_reason": normalized_reason,
            }
            result = self._view(order)
            self._audit(
                "payment.order.cancelled",
                result.id,
                user_id=principal.user_id,
                status=result.status,
                reason=normalized_reason,
            )
        return result

    async def get_fee_obligation_for_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> FeeObligationView:
        async with self._session.begin():
            dossier = await self._required_dossier(dossier_id)
            await self._require_access(principal, dossier)
            obligation = await self._billing.obligation_for_dossier(dossier_id)
            if obligation is None:
                raise PaymentNotFoundError("Fee obligation was not found.")
            if obligation.owner_user_id != principal.user_id:
                raise PaymentForbiddenError()
            return FeeObligationView(
                id=obligation.id,
                dossier_id=obligation.dossier_id,
                owner_user_id=obligation.owner_user_id,
                price_catalog_version_id=obligation.price_catalog_version_id,
                price_catalog_entry_id=obligation.price_catalog_entry_id,
                service_code=obligation.service_code,
                description=obligation.description,
                amount_minor=obligation.amount_minor,
                currency=obligation.currency,
                tax_mode=obligation.tax_mode,
                status=obligation.status,
                due_at=obligation.due_at,
                paid_at=obligation.paid_at,
            )

    async def process_webhook(
        self,
        *,
        raw_body: bytes,
        signature: str,
        timestamp: int,
    ) -> PaymentOrderView | None:
        try:
            event = self._gateway.verify_webhook(
                raw_body=raw_body,
                signature=signature,
                timestamp=timestamp,
                now=self._clock(),
            )
        except InvalidWebhookError as exc:
            raise PaymentInvalidWebhookError() from exc
        mismatch = False
        conflict_outcome: str | None = None
        newly_paid = False
        async with self._session.begin():
            duplicate = await self._payments.get_event(event.provider_event_id)
            if duplicate is not None:
                return self._view(
                    await self._required_order(duplicate.payment_order_id)
                )
            order = await self._payments.get_by_provider_order(
                self._provider_name,
                event.provider_order_id,
                for_update=True,
            )
            if order is None and event.order_code is not None:
                reserved = await self._payments.get_by_order_code(
                    event.order_code, for_update=True
                )
                if (
                    reserved is not None
                    and reserved.provider_order_id is None
                    and reserved.provider == self._provider_name
                ):
                    order = reserved
            if order is None:
                if await self.wallet_service().settle_event(event):
                    return None
                raise PaymentNotFoundError()
            payment_event = PaymentEvent(
                id=self._uuid_factory(),
                payment_order_id=order.id,
                provider_event_id=event.provider_event_id,
                event_type=event.event_type,
                signature_valid=True,
                payload_redacted=dict(event.payload_redacted),
            )
            self._payments.add_event(payment_event)
            if (
                event.amount_minor != order.amount_minor
                or event.currency != order.currency
                or (
                    event.order_code is not None
                    and event.order_code != order.order_code
                )
            ):
                mismatch = True
                payment_event.processed_at = self._clock()
            elif event.event_type == "payment.paid":
                if order.provider_order_id is None:
                    order.provider_order_id = event.provider_order_id
                if order.status in {
                    PaymentStatus.FAILED,
                    PaymentStatus.CANCELLED,
                    PaymentStatus.EXPIRED,
                    PaymentStatus.REFUNDED,
                }:
                    conflict_outcome = f"PAID_AFTER_{order.status.value}"
                elif order.status is not PaymentStatus.PAID:
                    dossier = await self._required_dossier(
                        order.dossier_id,
                        for_update=True,
                    )
                    self._workflow.transition(
                        dossier,
                        target=self._confirmed_dossier_status(dossier),
                        actor_user_id=dossier.owner_user_id,
                        allowed_sources={DossierStatus.PAYMENT_PENDING},
                        reason_code="PAYMENT_WEBHOOK_CONFIRMED",
                    )
                    self._transition_status(order, PaymentStatus.PAID, source="WEBHOOK")
                    order.paid_at = self._clock()
                    await self._settle_fee_obligation(order)
                    newly_paid = not dossier.submission_fee_required
                    await self._add_paid_notification(
                        dossier,
                        order,
                        source_event_id=payment_event.id,
                    )
                payment_event.processed_at = self._clock()
            elif event.event_type == "payment.failed":
                if order.status in {
                    PaymentStatus.PENDING,
                    PaymentStatus.PROCESSING,
                }:
                    self._transition_status(
                        order, PaymentStatus.FAILED, source="WEBHOOK"
                    )
                    await self._release_voucher(order, "Verified payment failure")
                payment_event.processed_at = self._clock()
            else:
                if order.status in {
                    PaymentStatus.PENDING,
                    PaymentStatus.PROCESSING,
                }:
                    self._transition_status(
                        order, PaymentStatus.PROCESSING, source="WEBHOOK"
                    )
                payment_event.processed_at = self._clock()
            await self._session.flush()
            await self._session.refresh(order)
            result = self._view(order)
            self._audit(
                (
                    "payment.webhook.rejected"
                    if mismatch
                    else (
                        "payment.webhook.conflict"
                        if conflict_outcome
                        else "payment.webhook.processed"
                    )
                ),
                result.id,
                actor_service="payment-webhook",
                outcome=(
                    "AMOUNT_MISMATCH"
                    if mismatch
                    else conflict_outcome or result.status.value
                ),
            )
        if mismatch:
            raise PaymentAmountMismatchError()
        if newly_paid and self._enqueue_certificate_issue is not None:
            self._enqueue_certificate_issue(result.dossier_id)
        return result

    async def reconcile_order(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
    ) -> PaymentOrderView:
        AuthorizationPolicy.require_capability(
            principal,
            RECONCILIATION_REQUIREMENT,
            PaymentForbiddenError,
        )
        result, should_issue = await self._reconcile_provider_order(
            order_id,
            user_id=principal.user_id,
        )
        if should_issue and self._enqueue_certificate_issue is not None:
            self._enqueue_certificate_issue(result.dossier_id)
        return result

    async def reconcile_pending(self, *, limit: int = 100) -> int:
        if limit < 1 or limit > 500:
            raise ValueError("Payment reconciliation limit is invalid.")
        async with self._session.begin():
            order_ids = tuple(
                order.id
                for order in await self._payments.list_reconcilable(limit=limit)
            )
        reconciled = 0
        for order_id in order_ids:
            try:
                async with self._session.begin():
                    order = await self._required_order(order_id)
                    needs_checkout = order.provider_order_id is None
                if needs_checkout:
                    await self._ensure_checkout(order_id)
                result, should_issue = await self._reconcile_provider_order(
                    order_id,
                    actor_service="payment-reconciliation-worker",
                )
            except (PaymentProviderError, PaymentAmountMismatchError):
                logger.exception(
                    "payment_reconciliation_failed",
                    extra={"payment_order_id": str(order_id)},
                )
                continue
            if should_issue and self._enqueue_certificate_issue is not None:
                self._enqueue_certificate_issue(result.dossier_id)
            reconciled += 1
        return reconciled + await self.wallet_service().reconcile_pending(
            limit - reconciled
        )

    async def _reconcile_provider_order(
        self,
        order_id: UUID,
        *,
        user_id: UUID | None = None,
        actor_service: str | None = None,
    ) -> tuple[PaymentOrderView, bool]:
        should_issue = False
        async with self._session.begin():
            order = await self._required_order(order_id)
            if order.status is PaymentStatus.PAID or order.provider == "wallet":
                return self._view(order), False
            provider_order_id = order.provider_order_id or order.order_code
        try:
            provider_order = await self._gateway.get_order(provider_order_id)
        except PaymentGatewayError as exc:
            raise PaymentProviderError() from exc
        async with self._session.begin():
            order = await self._required_order(order_id, for_update=True)
            previous_status = order.status
            if (
                order.status is PaymentStatus.PAID
                and provider_order.status != PaymentStatus.PAID.value
            ):
                # A delayed provider snapshot must not undo a verified webhook.
                return self._view(order), False
            if order.provider_order_id not in {None, provider_order_id}:
                raise PaymentConflictError(
                    "Provider order changed during reconciliation."
                )
            if order.provider_order_id is None:
                order.provider_order_id = provider_order.provider_order_id
                order.metadata_json = {
                    **order.metadata_json,
                    "checkout_url": provider_order.checkout_url,
                    "qr_payload": provider_order.qr_payload,
                }
            if (
                (
                    provider_order.order_code is not None
                    and provider_order.order_code != order.order_code
                )
                or (
                    provider_order.amount_minor is not None
                    and provider_order.amount_minor != order.amount_minor
                )
                or (
                    provider_order.currency is not None
                    and provider_order.currency != order.currency
                )
            ):
                raise PaymentAmountMismatchError()
            if order.status in {
                PaymentStatus.FAILED,
                PaymentStatus.CANCELLED,
                PaymentStatus.EXPIRED,
                PaymentStatus.REFUNDED,
            }:
                if provider_order.status == PaymentStatus.PAID.value:
                    self._audit(
                        "payment.reconciliation.conflict",
                        order.id,
                        user_id=user_id,
                        actor_service=actor_service,
                        outcome=f"PAID_AFTER_{order.status.value}",
                    )
                return self._view(order), False
            if provider_order.status == PaymentStatus.PAID.value:
                if order.status is not PaymentStatus.PAID:
                    dossier = await self._required_dossier(
                        order.dossier_id,
                        for_update=True,
                    )
                    self._workflow.transition(
                        dossier,
                        target=self._confirmed_dossier_status(dossier),
                        actor_user_id=dossier.owner_user_id,
                        allowed_sources={DossierStatus.PAYMENT_PENDING},
                        reason_code="PAYMENT_RECONCILIATION_CONFIRMED",
                    )
                    self._transition_status(
                        order,
                        PaymentStatus.PAID,
                        source="RECONCILIATION",
                        actor=user_id,
                    )
                    order.paid_at = self._clock()
                    await self._settle_fee_obligation(order)
                    should_issue = not dossier.submission_fee_required
                    await self._add_paid_notification(
                        dossier,
                        order,
                        source_event_id=uuid5(order.id, "payment-paid"),
                    )
            elif provider_order.status == "CANCELLED":
                dossier = await self._required_dossier(
                    order.dossier_id,
                    for_update=True,
                )
                self._workflow.transition(
                    dossier,
                    target=(
                        DossierStatus.PAYMENT_PENDING
                        if dossier.submission_fee_required
                        else DossierStatus.APPROVED
                    ),
                    actor_user_id=dossier.owner_user_id,
                    allowed_sources={DossierStatus.PAYMENT_PENDING},
                    reason_code="PAYMENT_RECONCILIATION_CANCELLED",
                )
                self._transition_status(
                    order,
                    PaymentStatus.CANCELLED,
                    source="RECONCILIATION",
                    actor=user_id,
                )
                await self._release_voucher(order, "Provider confirmed cancellation")
            elif provider_order.status == PaymentStatus.PROCESSING.value:
                self._transition_status(
                    order,
                    PaymentStatus.PROCESSING,
                    source="RECONCILIATION",
                    actor=user_id,
                )
            elif provider_order.status == PaymentStatus.PENDING.value:
                self._transition_status(
                    order,
                    PaymentStatus.PENDING,
                    source="RECONCILIATION",
                    actor=user_id,
                )
            elif provider_order.status == PaymentStatus.FAILED.value:
                self._transition_status(
                    order,
                    PaymentStatus.FAILED,
                    source="RECONCILIATION",
                    actor=user_id,
                )
                await self._release_voucher(order, "Provider confirmed failure")
            await self._expire_if_needed(order)
            await self._session.flush()
            await self._session.refresh(order)
            result = self._view(order)
            if result.status is not previous_status:
                self._audit(
                    "payment.order.reconciled",
                    result.id,
                    user_id=user_id,
                    actor_service=actor_service,
                    status=result.status,
                )
        return result, should_issue

    async def confirm_manual(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
        *,
        evidence_reference: str,
        note: str,
    ) -> PaymentOrderView:
        self._require_role(principal, FINANCE_ROLES)
        evidence = evidence_reference.strip()
        normalized_note = note.strip()
        if not evidence or len(evidence) > 255 or not normalized_note:
            raise PaymentConflictError("Manual confirmation evidence is required.")
        async with self._session.begin():
            order = await self._required_order(order_id, for_update=True)
            if order.status not in {
                PaymentStatus.PENDING,
                PaymentStatus.PROCESSING,
            }:
                raise PaymentConflictError(
                    "Only a pending payment can be manually confirmed."
                )
            dossier = await self._required_dossier(
                order.dossier_id,
                for_update=True,
            )
            self._workflow.transition(
                dossier,
                target=self._confirmed_dossier_status(dossier),
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.PAYMENT_PENDING},
                reason_code="PAYMENT_MANUAL_CONFIRMATION",
                note=normalized_note[:2_000],
            )
            self._transition_status(
                order,
                PaymentStatus.PAID,
                source="MANUAL_CONFIRMATION",
                actor=principal.user_id,
            )
            order.paid_at = self._clock()
            await self._settle_fee_obligation(order)
            order.metadata_json = {
                **order.metadata_json,
                "manual_evidence_reference": evidence,
            }
            await self._add_paid_notification(
                dossier,
                order,
                source_event_id=uuid5(order.id, "manual-payment-paid"),
            )
            await self._session.flush()
            await self._session.refresh(order)
            result = self._view(order)
            self._audit(
                "payment.order.manually_confirmed",
                result.id,
                user_id=principal.user_id,
                status=result.status,
            )
        if (
            not dossier.submission_fee_required
            and self._enqueue_certificate_issue is not None
        ):
            self._enqueue_certificate_issue(result.dossier_id)
        return result

    async def _required_dossier(
        self,
        dossier_id: UUID,
        *,
        for_update: bool = False,
    ) -> Dossier:
        dossier = await self._dossiers.get_by_id(
            dossier_id,
            for_update=for_update,
        )
        if dossier is None:
            raise PaymentNotFoundError("Dossier was not found.")
        return dossier

    async def _required_order(
        self,
        order_id: UUID,
        *,
        for_update: bool = False,
    ) -> PaymentOrder:
        order = await self._payments.get_order(order_id, for_update=for_update)
        if order is None:
            raise PaymentNotFoundError()
        return order

    async def _require_access(
        self,
        principal: AuthPrincipal,
        dossier: Dossier,
    ) -> None:
        if not await self._payments.can_access_dossier(
            principal.user_id,
            dossier,
        ):
            raise PaymentForbiddenError()

    @staticmethod
    def _require_role(
        principal: AuthPrincipal,
        allowed: frozenset[str],
    ) -> None:
        requirement = PAYMENT_REQUIREMENTS.get(allowed)
        if requirement is None:
            raise PaymentForbiddenError()
        AuthorizationPolicy.require_capability(
            principal, requirement, PaymentForbiddenError
        )

    async def _expire_if_needed(self, order: PaymentOrder) -> None:
        expires_at = order.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if (
            order.status in {PaymentStatus.PENDING, PaymentStatus.PROCESSING}
            and expires_at <= self._clock()
        ):
            # A provider-backed timeout is ambiguous and must stay held until
            # reconciliation. A never-started local request has no external payer.
            never_started = (
                order.provider_order_id is None
                and order.status is PaymentStatus.PENDING
            )
            self._transition_status(order, PaymentStatus.EXPIRED, source="EXPIRY")
            if never_started:
                await self._release_voucher(
                    order, "Local checkout expired before provider initialization"
                )

    def _record_initial_status(
        self,
        order: PaymentOrder,
        *,
        source: str,
        actor: UUID | None,
    ) -> None:
        changed_at = self._next_status_history_time(order)
        self._payments.add_status_history(
            PaymentStatusHistory(
                payment_order_id=order.id,
                from_status=None,
                to_status=order.status.value,
                source=source,
                actor_user_id=actor,
                changed_at=changed_at,
            )
        )

    def _transition_status(
        self,
        order: PaymentOrder,
        target: PaymentStatus,
        *,
        source: str,
        actor: UUID | None = None,
    ) -> None:
        previous = order.status
        if previous is target:
            return
        order.status = target
        changed_at = self._next_status_history_time(order)
        self._payments.add_status_history(
            PaymentStatusHistory(
                payment_order_id=order.id,
                from_status=previous.value,
                to_status=target.value,
                source=source,
                actor_user_id=actor,
                changed_at=changed_at,
            )
        )

    def _next_status_history_time(self, order: PaymentOrder) -> datetime:
        changed_at = self._utc(self._clock())
        previous = self._metadata_datetime(
            order.metadata_json.get("status_history_changed_at")
        )
        if previous is not None:
            previous = self._utc(previous)
            if changed_at <= previous:
                changed_at = previous + timedelta(microseconds=1)
        order.metadata_json = {
            **order.metadata_json,
            "status_history_changed_at": changed_at.isoformat(),
        }
        return changed_at

    @staticmethod
    def _validate_provider_order(
        order: PaymentOrder, provider_order: ProviderOrder
    ) -> None:
        if (
            (
                provider_order.order_code is not None
                and provider_order.order_code != order.order_code
            )
            or (
                provider_order.amount_minor is not None
                and provider_order.amount_minor != order.amount_minor
            )
            or (
                provider_order.currency is not None
                and provider_order.currency != order.currency
            )
        ):
            raise PaymentAmountMismatchError()

    @staticmethod
    def _view(order: PaymentOrder) -> PaymentOrderView:
        checkout = order.metadata_json.get("checkout_url")
        qr_payload = order.metadata_json.get("qr_payload")
        description = order.metadata_json.get("description")
        due_at = PaymentService._metadata_datetime(order.metadata_json.get("due_at"))
        issued_at = PaymentService._metadata_datetime(
            order.metadata_json.get("issued_at")
        )
        issued_by = order.metadata_json.get("issued_by_user_id")
        bank_bin = order.metadata_json.get("bank_bin")
        bank_account_number = order.metadata_json.get("bank_account_number")
        bank_account_name = order.metadata_json.get("bank_account_name")
        transfer_description = order.metadata_json.get("transfer_description")
        return PaymentOrderView(
            id=order.id,
            order_code=order.order_code,
            dossier_id=order.dossier_id,
            fee_obligation_id=order.fee_obligation_id,
            purpose=str(order.metadata_json["purpose"])
            if order.metadata_json.get("purpose")
            else None,
            provider=order.provider,
            provider_order_id=order.provider_order_id,
            amount_minor=order.amount_minor,
            currency=order.currency,
            status=order.status,
            expires_at=PaymentService._utc(order.expires_at),
            paid_at=PaymentService._utc(order.paid_at) if order.paid_at else None,
            checkout_url=checkout if isinstance(checkout, str) else None,
            qr_payload=qr_payload if isinstance(qr_payload, str) else None,
            created_at=PaymentService._utc(order.created_at),
            updated_at=PaymentService._utc(order.updated_at),
            description=description if isinstance(description, str) else None,
            due_at=due_at,
            issued_by_user_id=UUID(issued_by) if isinstance(issued_by, str) else None,
            issued_at=issued_at,
            bank_bin=bank_bin if isinstance(bank_bin, str) else None,
            bank_account_number=(
                bank_account_number if isinstance(bank_account_number, str) else None
            ),
            bank_account_name=(
                bank_account_name if isinstance(bank_account_name, str) else None
            ),
            transfer_description=(
                transfer_description if isinstance(transfer_description, str) else None
            ),
        )

    @staticmethod
    def _metadata_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value

    def _confirmed_dossier_status(self, dossier: Dossier) -> DossierStatus:
        if dossier.submission_fee_required:
            dossier.submission_fee_paid_at = self._clock()
            return DossierStatus.SUBMITTED
        return DossierStatus.PAID

    async def _add_paid_notification(
        self,
        dossier: Dossier,
        order: PaymentOrder,
        *,
        source_event_id: UUID,
    ) -> None:
        if dossier.submission_fee_required:
            self._session.add(
                Notification(
                    user_id=dossier.owner_user_id,
                    source_event_id=source_event_id,
                    type="PAYMENT_CONFIRMED",
                    title="Đã thanh toán phí nộp hồ sơ",
                    body=(
                        "Hồ sơ đã được tiếp nhận và chờ kiểm tra, thẩm định. "
                        "Không cần nộp lại phí khi bổ sung hồ sơ."
                    ),
                    data_json={
                        "dossierId": str(dossier.id),
                        "paymentOrderId": str(order.id),
                        "actionPath": f"/dossiers/{dossier.id}",
                    },
                    created_at=self._clock(),
                )
            )
            return
        self._session.add(
            Notification(
                user_id=dossier.owner_user_id,
                source_event_id=source_event_id,
                type="PAYMENT_CONFIRMED",
                title="Thanh toán đã được xác nhận",
                body=(
                    "Hồ sơ đang được đưa vào quy trình ký blockchain "
                    "và phát hành bằng xác lập."
                ),
                data_json={
                    "dossierId": str(dossier.id),
                    "paymentOrderId": str(order.id),
                    "actionPath": f"/dossiers/{dossier.id}",
                },
                created_at=self._clock(),
            )
        )
        await self._add_admin_ready_notifications(
            dossier,
            source_event_id=uuid5(source_event_id, "admin-ready"),
            body=(
                f"Đã xác nhận {order.amount_minor:,} {order.currency}; "
                "hồ sơ sẵn sàng để ký blockchain."
            ),
        )

    async def _add_admin_ready_notifications(
        self,
        dossier: Dossier,
        *,
        source_event_id: UUID,
        body: str,
    ) -> None:
        for user_id in await self._auth.list_user_ids_by_role_codes(FINANCE_ROLES):
            self._session.add(
                Notification(
                    user_id=user_id,
                    source_event_id=source_event_id,
                    type="DOSSIER_READY_FOR_BLOCKCHAIN",
                    title="Hồ sơ sẵn sàng ký blockchain",
                    body=body,
                    data_json={
                        "dossierId": str(dossier.id),
                        "actionPath": "/blockchain",
                    },
                    created_at=self._clock(),
                )
            )

    async def _release_voucher(self, order: PaymentOrder, reason: str) -> None:
        if order.metadata_json.get("voucher_id"):
            from app.modules.promotions.checkout import PromotionCheckout

            await PromotionCheckout(self._session, now=self._clock()).release(
                f"payment:{order.id}", reason=reason
            )

    async def _settle_fee_obligation(self, order: PaymentOrder) -> None:
        if order.metadata_json.get("voucher_id"):
            from app.modules.promotions.checkout import PromotionCheckout

            await PromotionCheckout(self._session, now=self._clock()).redeem(
                f"payment:{order.id}"
            )
        if order.fee_obligation_id is None:
            return
        obligation = await self._billing.obligation_by_id(
            order.fee_obligation_id, for_update=True
        )
        if obligation is None:
            raise PaymentConflictError("Linked fee obligation was not found.")
        if obligation.status not in {
            FeeObligationStatus.OPEN,
            FeeObligationStatus.OVERDUE,
            FeeObligationStatus.PAID,
        }:
            raise PaymentConflictError("Linked fee obligation is not payable.")
        obligation.status = FeeObligationStatus.PAID
        obligation.paid_at = order.paid_at

    def _audit(
        self,
        action: str,
        aggregate_id: UUID,
        *,
        user_id: UUID | None = None,
        actor_service: str | None = None,
        status: PaymentStatus | None = None,
        outcome: str | None = None,
        reason: str | None = None,
    ) -> None:
        after: dict[str, object] = {}
        if status is not None:
            after["status"] = status.value
        if outcome is not None:
            after["outcome"] = outcome
        if reason is not None:
            after["reason"] = reason
        self._audit_service.record(
            actor_user_id=user_id,
            actor_service=actor_service,
            action=action,
            resource_type="payment_order",
            resource_id=str(aggregate_id),
            after=after or None,
        )

    async def close(self) -> None:
        await self._gateway.close()
        await self._session.close()
