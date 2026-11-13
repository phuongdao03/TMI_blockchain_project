"""Create immutable submission fee obligations after applicant consent."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.errors import PriceCatalogConflictError
from app.modules.billing.fees import FeePolicyService
from app.modules.billing.models import (
    FeeObligation,
    FeeObligationStatus,
    FeePolicy,
    FeePolicyStatus,
)
from app.modules.billing.repository import BillingRepository
from app.modules.dossiers.models import Dossier, DossierStatus
from app.modules.payments.models import (
    PaymentOrder,
    PaymentStatus,
    PaymentStatusHistory,
)
from app.modules.payments.repository import PaymentRepository

FEE_TYPE = "DOSSIER_SUBMISSION"
NO_FEE_QUOTE = {
    "feeRequired": False,
    "feeAvailable": True,
    "amountMinor": 0,
    "currency": "VND",
    "description": "Hiện chưa có phí nộp hồ sơ áp dụng cho loại hồ sơ này.",
    "policyId": None,
    "policyVersionNo": None,
}
UNAVAILABLE_FEE_QUOTE = {
    "feeRequired": True,
    "feeAvailable": False,
    "amountMinor": 0,
    "currency": "VND",
    "description": (
        "Ch\u01b0a c\u00f3 ch\u00ednh s\u00e1ch ph\u00ed n\u1ed9p "
        "h\u1ed3 s\u01a1 chung \u0111ang c\u00f3 hi\u1ec7u l\u1ef1c. "
        "B\u1ea3n nh\u00e1p v\u1eabn \u0111\u01b0\u1ee3c l\u01b0u; vui l\u00f2ng "
        "th\u1eed l\u1ea1i sau khi Admin k\u00edch ho\u1ea1t ch\u00ednh s\u00e1ch."
    ),
    "policyId": None,
    "policyVersionNo": None,
}


class SubmissionFeeService:
    def __init__(self, session: AsyncSession, *, now: datetime) -> None:
        self.session = session
        self.now = self._aware(now)
        self.payments = PaymentRepository(session)
        self._policies = FeePolicyService(session, clock=lambda: self.now)
        self._billing = BillingRepository(session)

    async def quote(self, dossier: Dossier) -> dict[str, object]:
        if dossier.submission_fee_snapshot is not None:
            snapshot = dict(dossier.submission_fee_snapshot)
            snapshot.setdefault("feeRequired", True)
            snapshot.setdefault("feeAvailable", True)
            snapshot.setdefault("policyId", None)
            snapshot.setdefault("policyVersionNo", None)
            return snapshot
        if dossier.submission_fee_policy_mode != "DYNAMIC":
            return dict(NO_FEE_QUOTE)
        policy = await self._policies.resolve(
            fee_type=FEE_TYPE,
            dossier_type_id=None,
            at=self.now,
        )
        if policy is None:
            return dict(UNAVAILABLE_FEE_QUOTE)
        return {
            "feeRequired": True,
            "feeAvailable": True,
            "amountMinor": policy.amount_minor,
            "currency": policy.currency,
            "description": policy.display_name,
            "policyId": str(policy.id),
            "policyVersionNo": policy.version_no,
        }

    async def reserve(
        self,
        dossier: Dossier,
        *,
        actor: UUID,
        key: str,
        accepted_policy_version: int | None,
    ) -> PaymentOrder | None:
        if dossier.status not in {
            DossierStatus.DRAFT,
            DossierStatus.SUBMITTED,
            DossierStatus.PAYMENT_PENDING,
        }:
            raise PriceCatalogConflictError(
                "Submit the dossier before reserving its fee."
            )
        if (
            dossier.submission_fee_paid_at is not None
            or dossier.submission_fee_waived_at is not None
        ):
            return None
        replay = await self.payments.get_by_idempotency(key)
        if replay is not None:
            if replay.dossier_id != dossier.id:
                raise PriceCatalogConflictError("Payment key is already in use.")
            return replay
        active = await self.payments.get_active_for_dossier(dossier.id)
        if active is not None:
            if self._aware(active.expires_at) > self.now:
                return active
            active.status = PaymentStatus.EXPIRED
            self.session.add(
                PaymentStatusHistory(
                    payment_order_id=active.id,
                    from_status="PENDING",
                    to_status="EXPIRED",
                    source="SUBMISSION_FEE_EXPIRED",
                    actor_user_id=actor,
                    changed_at=self.now,
                )
            )

        # Legacy rows without immutable amounts are never assigned a new rate.
        if dossier.submission_fee_policy_mode != "DYNAMIC":
            legacy_snapshot = dossier.submission_fee_snapshot
            if dossier.submission_fee_required and legacy_snapshot is not None:
                amount = legacy_snapshot.get("amountMinor")
                if isinstance(amount, int) and amount > 0:
                    return await self._legacy_order(
                        dossier,
                        actor=actor,
                        key=key,
                        amount=amount,
                        description=str(
                            legacy_snapshot.get("description", "Phí nộp hồ sơ")
                        ),
                    )
            dossier.submission_fee_required = False
            return None
        existing_snapshot = dossier.submission_fee_snapshot
        quote = (
            dict(existing_snapshot)
            if existing_snapshot is not None
            else await self.quote(dossier)
        )
        if quote.get("feeAvailable") is False:
            raise PriceCatalogConflictError(
                "No approved submission fee policy is available for this dossier.",
                code="FEE_POLICY_UNAVAILABLE",
                details={"currentQuote": quote},
            )
        current_version = quote.get("policyVersionNo")
        if existing_snapshot is None and current_version != accepted_policy_version:
            raise PriceCatalogConflictError(
                "The submission fee changed. Review and accept the current amount.",
                code="FEE_QUOTE_STALE",
                details={"currentQuote": quote},
            )
        if quote.get("feeRequired") is not True:
            dossier.submission_fee_required = False
            return None
        amount = quote.get("amountMinor")
        policy_id = quote.get("policyId")
        if not isinstance(amount, int) or not isinstance(policy_id, str):
            raise PriceCatalogConflictError("Current submission fee is invalid.")
        waiver_amount = quote.get("waiverAmountMinor")
        if not isinstance(waiver_amount, int):
            waiver_amount = await self._policies.apply_approved_waiver(
                dossier_id=dossier.id,
                fee_type=FEE_TYPE,
                gross_amount_minor=amount,
                actor_user_id=actor,
            )
        due_amount = (
            quote.get("amountMinor") if existing_snapshot else amount - waiver_amount
        )
        if not isinstance(due_amount, int) or due_amount < 0:
            raise PriceCatalogConflictError("Submission fee due amount is invalid.")
        policy = await self.session.scalar(
            select(FeePolicy).where(FeePolicy.id == UUID(policy_id))
        )
        if policy is None or policy.status not in {
            FeePolicyStatus.ACTIVE,
            FeePolicyStatus.SCHEDULED,
            FeePolicyStatus.EXPIRED,
        }:
            raise PriceCatalogConflictError(
                "Submission fee policy changed during confirmation."
            )
        obligation = await self._billing.obligation_for_dossier(
            dossier.id, fee_type=FEE_TYPE
        )
        if obligation is None:
            obligation = FeeObligation(
                id=uuid4(),
                dossier_id=dossier.id,
                is_test=dossier.is_test,
                owner_user_id=dossier.owner_user_id,
                price_catalog_version_id=None,
                price_catalog_entry_id=None,
                service_code=FEE_TYPE,
                description=str(quote["description"]),
                amount_minor=due_amount,
                currency="VND",
                tax_mode="UNSPECIFIED",
                status=(
                    FeeObligationStatus.WAIVED
                    if due_amount == 0
                    else FeeObligationStatus.OPEN
                ),
                due_at=self.now + timedelta(days=7),
                paid_at=self.now if due_amount == 0 else None,
                price_snapshot_json={
                    **quote,
                    "feeType": FEE_TYPE,
                    "grossAmountMinor": amount,
                    "waiverAmountMinor": waiver_amount,
                    "amountMinor": due_amount,
                },
                fee_type=FEE_TYPE,
                fee_policy_id=policy.id,
                fee_policy_version_no=policy.version_no,
                gross_amount_minor=amount,
                waiver_amount_minor=waiver_amount,
            )
            self._billing.add_obligation(obligation)
        dossier.submission_fee_required = True
        dossier.submission_fee_snapshot = {
            **quote,
            "feeType": FEE_TYPE,
            "grossAmountMinor": amount,
            "waiverAmountMinor": waiver_amount,
            "amountMinor": due_amount,
        }
        if due_amount == 0:
            dossier.submission_fee_waived_at = self.now
            await self.session.flush()
            return None

        identifier = uuid4()
        order = PaymentOrder(
            id=identifier,
            order_code=str(identifier.int % 10**31),
            dossier_id=dossier.id,
            is_test=dossier.is_test,
            fee_obligation_id=obligation.id,
            initiated_by_user_id=actor,
            provider="test" if dossier.is_test else "wallet",
            amount_minor=due_amount,
            currency="VND",
            status=PaymentStatus.PENDING,
            expires_at=self.now + timedelta(days=7),
            idempotency_key=key,
            metadata_json={
                "description": quote["description"],
                "purpose": FEE_TYPE,
                "feePolicyId": policy_id,
                "feePolicyVersionNo": current_version,
            },
        )
        self.session.add(order)
        self.session.add(
            PaymentStatusHistory(
                payment_order_id=identifier,
                from_status=None,
                to_status="PENDING",
                source="SUBMISSION_FEE_CREATED",
                actor_user_id=actor,
                changed_at=self.now,
            )
        )
        await self.session.flush()
        return order

    async def _legacy_order(
        self,
        dossier: Dossier,
        *,
        actor: UUID,
        key: str,
        amount: int,
        description: str,
    ) -> PaymentOrder:
        identifier = uuid4()
        order = PaymentOrder(
            id=identifier,
            order_code=str(identifier.int % 10**31),
            dossier_id=dossier.id,
            is_test=dossier.is_test,
            initiated_by_user_id=actor,
            provider="wallet",
            amount_minor=amount,
            currency="VND",
            status=PaymentStatus.PENDING,
            expires_at=self.now + timedelta(days=7),
            idempotency_key=key,
            metadata_json={"description": description, "purpose": "SUBMISSION_FEE"},
        )
        self.session.add(order)
        self.session.add(
            PaymentStatusHistory(
                payment_order_id=identifier,
                from_status=None,
                to_status="PENDING",
                source="SUBMISSION_FEE_CREATED",
                actor_user_id=actor,
                changed_at=self.now,
            )
        )
        await self.session.flush()
        return order

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )
