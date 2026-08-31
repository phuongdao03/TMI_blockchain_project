import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.billing.models import FeeObligationStatus
from app.modules.billing.repository import BillingRepository
from app.modules.billing.service import FeeObligationView
from app.modules.dossiers.models import Dossier, DossierStatus
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.workflow import DossierWorkflowService
from app.modules.notifications.models import Notification
from app.modules.payments.errors import (
    PaymentAmountMismatchError,
    PaymentConflictError,
    PaymentForbiddenError,
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
from app.modules.payments.models import PaymentEvent, PaymentOrder, PaymentStatus
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.types import PaymentOrderView

logger = logging.getLogger(__name__)

PAYMENT_ROLES = frozenset({"USER"})
FINANCE_ROLES = frozenset({"SUPER_ADMIN"})
RECONCILIATION_REQUIREMENT = PolicyRequirement(
    permission="payments.reconcile",
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
        self._billing = BillingRepository(session)
        self._audit_service = AuditService(session)
        self._dossiers = DossierRepository(session)
        self._workflow = DossierWorkflowService(self._dossiers)

    @property
    def provider_name(self) -> str:
        return self._provider_name

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
        async with self._session.begin():
            replay = await self._payments.get_by_idempotency(normalized_key)
            if replay is not None:
                dossier = await self._required_dossier(replay.dossier_id)
                await self._require_access(principal, dossier)
                return self._view(replay)
            dossier = await self._required_dossier(dossier_id, for_update=True)
            await self._require_access(principal, dossier)
            if dossier.status is not DossierStatus.APPROVED:
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
            self._audit(
                "payment.order.created",
                order_id,
                user_id=principal.user_id,
                status=PaymentStatus.PENDING,
            )
            try:
                provider_order = await self._gateway.create_order(
                    order_code=order_code,
                    amount_minor=self._amount_minor,
                    currency=self._currency,
                    expires_at=expires_at,
                )
            except PaymentGatewayError as exc:
                raise PaymentProviderError() from exc
            order = PaymentOrder(
                id=order_id,
                order_code=order_code,
                dossier_id=dossier.id,
                provider=self._provider_name,
                provider_order_id=provider_order.provider_order_id,
                amount_minor=self._amount_minor,
                currency=self._currency,
                status=PaymentStatus.PENDING,
                expires_at=expires_at,
                idempotency_key=normalized_key,
                metadata_json={
                    "checkout_url": provider_order.checkout_url,
                    "qr_payload": provider_order.qr_payload,
                },
            )
            self._payments.add_order(order)
            self._workflow.transition(
                dossier,
                target=DossierStatus.PAYMENT_PENDING,
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.APPROVED},
                reason_code="PAYMENT_ORDER_CREATED",
            )
            await self._session.flush()
            result = self._view(order)
        return result

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
        certificate_dossier_id: UUID | None = None
        result: PaymentOrderView | None = None
        async with self._session.begin():
            replay = await self._payments.get_by_idempotency(normalized_key)
            if replay is not None:
                if replay.fee_obligation_id != obligation_id:
                    raise PaymentConflictError("Idempotency key is already in use.")
                dossier = await self._required_dossier(replay.dossier_id)
                await self._require_access(principal, dossier)
                return self._view(replay)
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
                self._expire_if_needed(active)
                if active.status in {
                    PaymentStatus.PENDING,
                    PaymentStatus.PROCESSING,
                }:
                    return self._view(active)
                if active.provider_order_id is not None:
                    try:
                        provider_state = await self._gateway.get_order(
                            active.provider_order_id
                        )
                    except PaymentGatewayError as exc:
                        raise PaymentProviderError() from exc
                    self._validate_provider_order(active, provider_state)
                    if provider_state.status == PaymentStatus.PAID.value:
                        self._workflow.transition(
                            dossier,
                            target=DossierStatus.PAID,
                            actor_user_id=principal.user_id,
                            allowed_sources={DossierStatus.PAYMENT_PENDING},
                            reason_code="PAYMENT_CHECKOUT_RECHECK_CONFIRMED",
                        )
                        active.status = PaymentStatus.PAID
                        active.paid_at = self._clock()
                        await self._settle_fee_obligation(active)
                        self._add_paid_notification(
                            dossier,
                            active,
                            source_event_id=uuid5(active.id, "payment-paid"),
                        )
                        await self._session.flush()
                        await self._session.refresh(active)
                        result = self._view(active)
                        certificate_dossier_id = dossier.id
            if result is None:
                order_id = self._uuid_factory()
                order_code = str((order_id.int % 2_147_483_646) + 1)
                due_at = obligation.due_at
                if due_at.tzinfo is None:
                    due_at = due_at.replace(tzinfo=UTC)
                expires_at = min(self._clock() + self._order_ttl, due_at)
                try:
                    provider_order = await self._gateway.create_order(
                        order_code=order_code,
                        amount_minor=obligation.amount_minor,
                        currency=obligation.currency,
                        expires_at=expires_at,
                    )
                except PaymentGatewayError as exc:
                    raise PaymentProviderError() from exc
                order = PaymentOrder(
                    id=order_id,
                    order_code=order_code,
                    dossier_id=dossier.id,
                    fee_obligation_id=obligation.id,
                    provider=self._provider_name,
                    provider_order_id=provider_order.provider_order_id,
                    amount_minor=obligation.amount_minor,
                    currency=obligation.currency,
                    status=PaymentStatus.PENDING,
                    expires_at=expires_at,
                    idempotency_key=normalized_key,
                    metadata_json={
                        "checkout_url": provider_order.checkout_url,
                        "qr_payload": provider_order.qr_payload,
                        "description": obligation.description,
                        "due_at": obligation.due_at.isoformat(),
                    },
                )
                self._payments.add_order(order)
                self._audit(
                    "payment.checkout.created",
                    order.id,
                    user_id=principal.user_id,
                    status=PaymentStatus.PENDING,
                )
                result = self._view(order)
            await self._session.flush()
        if (
            certificate_dossier_id is not None
            and self._enqueue_certificate_issue is not None
        ):
            self._enqueue_certificate_issue(certificate_dossier_id)
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

        async with self._session.begin():
            replay = await self._payments.get_by_idempotency(normalized_key)
            if replay is not None:
                return self._view(replay)
            dossier = await self._required_dossier(dossier_id, for_update=True)
            if dossier.status is not DossierStatus.APPROVED:
                raise PaymentConflictError(
                    "Only an approved dossier can receive a payment request."
                )
            if await self._payments.get_active_for_dossier(dossier.id):
                raise PaymentConflictError(
                    "This dossier already has an active payment request."
                )
            order_id = self._uuid_factory()
            order_code = str((order_id.int % 2_147_483_646) + 1)
            provider_expires_at = now + self._order_ttl
            expires_at = (
                min(provider_expires_at, normalized_due_at)
                if normalized_due_at
                else provider_expires_at
            )
            try:
                provider_order = await self._gateway.create_order(
                    order_code=order_code,
                    amount_minor=amount_minor,
                    currency=normalized_currency,
                    expires_at=expires_at,
                )
            except PaymentGatewayError as exc:
                raise PaymentProviderError() from exc
            order = PaymentOrder(
                id=order_id,
                order_code=order_code,
                dossier_id=dossier.id,
                provider=self._provider_name,
                provider_order_id=provider_order.provider_order_id,
                amount_minor=amount_minor,
                currency=normalized_currency,
                status=PaymentStatus.PENDING,
                expires_at=expires_at,
                idempotency_key=normalized_key,
                metadata_json={
                    "checkout_url": provider_order.checkout_url,
                    "qr_payload": provider_order.qr_payload,
                    "description": normalized_description,
                    "due_at": normalized_due_at.isoformat()
                    if normalized_due_at
                    else None,
                    "issued_by_user_id": str(principal.user_id),
                    "issued_at": now.isoformat(),
                },
            )
            self._payments.add_order(order)
            self._workflow.transition(
                dossier,
                target=DossierStatus.PAYMENT_PENDING,
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.APPROVED},
                reason_code="PAYMENT_REQUEST_ISSUED",
                note=normalized_description,
            )
            self._session.add(
                Notification(
                    user_id=dossier.owner_user_id,
                    source_event_id=order_id,
                    type="PAYMENT_REQUEST_ISSUED",
                    title="Hồ sơ có yêu cầu thanh toán",
                    body=f"Số tiền cần thanh toán: {amount_minor:,} VND.",
                    data_json={
                        "dossierId": str(dossier.id),
                        "paymentOrderId": str(order_id),
                    },
                    created_at=now,
                )
            )
            self._audit(
                "payment.request.issued",
                order_id,
                user_id=principal.user_id,
                status=PaymentStatus.PENDING,
                reason=normalized_description,
            )
            await self._session.flush()
            return self._view(order)

    async def get_order(
        self,
        principal: AuthPrincipal,
        order_id: UUID,
    ) -> PaymentOrderView:
        async with self._session.begin():
            order = await self._required_order(order_id)
            dossier = await self._required_dossier(order.dossier_id)
            await self._require_access(principal, dossier)
            self._expire_if_needed(order)
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
            self._expire_if_needed(order)
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
            self._expire_if_needed(order)
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
            order = await self._required_order(order_id, for_update=True)
            dossier = await self._required_dossier(order.dossier_id, for_update=True)
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
                raise PaymentConflictError("Provider order is not initialized.")
            try:
                provider_order = await self._gateway.cancel_order(
                    order.provider_order_id,
                    reason=normalized_reason,
                )
            except PaymentGatewayError as exc:
                raise PaymentProviderError() from exc
            if provider_order.status != PaymentStatus.CANCELLED.value:
                raise PaymentProviderError("Provider did not cancel the order.")
            self._workflow.transition(
                dossier,
                target=DossierStatus.APPROVED,
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.PAYMENT_PENDING},
                reason_code="PAYMENT_ORDER_CANCELLED",
                note=normalized_reason,
            )
            order.status = PaymentStatus.CANCELLED
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
    ) -> PaymentOrderView:
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
            if order is None:
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
                if order.status is not PaymentStatus.PAID:
                    dossier = await self._required_dossier(
                        order.dossier_id,
                        for_update=True,
                    )
                    self._workflow.transition(
                        dossier,
                        target=DossierStatus.PAID,
                        actor_user_id=dossier.owner_user_id,
                        allowed_sources={DossierStatus.PAYMENT_PENDING},
                        reason_code="PAYMENT_WEBHOOK_CONFIRMED",
                    )
                    order.status = PaymentStatus.PAID
                    order.paid_at = self._clock()
                    await self._settle_fee_obligation(order)
                    self._add_paid_notification(
                        dossier,
                        order,
                        source_event_id=payment_event.id,
                    )
                payment_event.processed_at = self._clock()
            elif event.event_type == "payment.failed":
                order.status = PaymentStatus.FAILED
                payment_event.processed_at = self._clock()
            else:
                order.status = PaymentStatus.PROCESSING
                payment_event.processed_at = self._clock()
            await self._session.flush()
            await self._session.refresh(order)
            result = self._view(order)
            self._audit(
                (
                    "payment.webhook.rejected"
                    if mismatch
                    else "payment.webhook.processed"
                ),
                result.id,
                actor_service="payment-webhook",
                outcome="AMOUNT_MISMATCH" if mismatch else result.status.value,
            )
        if mismatch:
            raise PaymentAmountMismatchError()
        if (
            result.status is PaymentStatus.PAID
            and self._enqueue_certificate_issue is not None
        ):
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
        return reconciled

    async def _reconcile_provider_order(
        self,
        order_id: UUID,
        *,
        user_id: UUID | None = None,
        actor_service: str | None = None,
    ) -> tuple[PaymentOrderView, bool]:
        should_issue = False
        async with self._session.begin():
            order = await self._required_order(order_id, for_update=True)
            previous_status = order.status
            if order.provider_order_id is None:
                raise PaymentConflictError("Provider order is not initialized.")
            try:
                provider_order = await self._gateway.get_order(order.provider_order_id)
            except PaymentGatewayError as exc:
                raise PaymentProviderError() from exc
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
            if provider_order.status == PaymentStatus.PAID.value:
                if order.status is not PaymentStatus.PAID:
                    dossier = await self._required_dossier(
                        order.dossier_id,
                        for_update=True,
                    )
                    self._workflow.transition(
                        dossier,
                        target=DossierStatus.PAID,
                        actor_user_id=dossier.owner_user_id,
                        allowed_sources={DossierStatus.PAYMENT_PENDING},
                        reason_code="PAYMENT_RECONCILIATION_CONFIRMED",
                    )
                    order.status = PaymentStatus.PAID
                    order.paid_at = self._clock()
                    await self._settle_fee_obligation(order)
                    should_issue = True
                    self._add_paid_notification(
                        dossier,
                        order,
                        source_event_id=uuid5(order.id, "payment-paid"),
                    )
            elif provider_order.status == "CANCELLED":
                if order.status is not PaymentStatus.CANCELLED:
                    dossier = await self._required_dossier(
                        order.dossier_id,
                        for_update=True,
                    )
                    self._workflow.transition(
                        dossier,
                        target=DossierStatus.APPROVED,
                        actor_user_id=dossier.owner_user_id,
                        allowed_sources={DossierStatus.PAYMENT_PENDING},
                        reason_code="PAYMENT_RECONCILIATION_CANCELLED",
                    )
                order.status = PaymentStatus.CANCELLED
            elif provider_order.status == PaymentStatus.PROCESSING.value:
                order.status = PaymentStatus.PROCESSING
            elif provider_order.status == PaymentStatus.FAILED.value:
                order.status = PaymentStatus.FAILED
            self._expire_if_needed(order)
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
                target=DossierStatus.PAID,
                actor_user_id=principal.user_id,
                allowed_sources={DossierStatus.PAYMENT_PENDING},
                reason_code="PAYMENT_MANUAL_CONFIRMATION",
                note=normalized_note[:2_000],
            )
            order.status = PaymentStatus.PAID
            order.paid_at = self._clock()
            await self._settle_fee_obligation(order)
            order.metadata_json = {
                **order.metadata_json,
                "manual_evidence_reference": evidence,
            }
            result = self._view(order)
            self._audit(
                "payment.order.manually_confirmed",
                result.id,
                user_id=principal.user_id,
                status=result.status,
            )
        if self._enqueue_certificate_issue is not None:
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

    def _expire_if_needed(self, order: PaymentOrder) -> None:
        expires_at = order.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if (
            order.status in {PaymentStatus.PENDING, PaymentStatus.PROCESSING}
            and expires_at <= self._clock()
        ):
            order.status = PaymentStatus.EXPIRED

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
        return PaymentOrderView(
            id=order.id,
            order_code=order.order_code,
            dossier_id=order.dossier_id,
            fee_obligation_id=order.fee_obligation_id,
            provider=order.provider,
            provider_order_id=order.provider_order_id,
            amount_minor=order.amount_minor,
            currency=order.currency,
            status=order.status,
            expires_at=order.expires_at,
            paid_at=order.paid_at,
            checkout_url=checkout if isinstance(checkout, str) else None,
            qr_payload=qr_payload if isinstance(qr_payload, str) else None,
            created_at=order.created_at,
            updated_at=order.updated_at,
            description=description if isinstance(description, str) else None,
            due_at=due_at,
            issued_by_user_id=UUID(issued_by) if isinstance(issued_by, str) else None,
            issued_at=issued_at,
        )

    @staticmethod
    def _metadata_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _add_paid_notification(
        self,
        dossier: Dossier,
        order: PaymentOrder,
        *,
        source_event_id: UUID,
    ) -> None:
        self._session.add(
            Notification(
                user_id=dossier.owner_user_id,
                source_event_id=source_event_id,
                type="PAYMENT_CONFIRMED",
                title="Thanh toán đã được xác nhận",
                body=(
                    "Hồ sơ đang được đưa vào quy trình ký blockchain "
                    "và phát hành chứng thư."
                ),
                data_json={
                    "dossierId": str(dossier.id),
                    "paymentOrderId": str(order.id),
                },
                created_at=self._clock(),
            )
        )

    async def _settle_fee_obligation(self, order: PaymentOrder) -> None:
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
