from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.billing.errors import PriceCatalogConflictError
from app.modules.billing.models import (
    FeeObligation,
    FeeObligationStatus,
    FeePolicy,
    FeePolicyEvent,
    FeePolicyStatus,
    FeeWaiver,
    FeeWaiverStatus,
)
from app.modules.dossiers.models import Dossier, DossierStatus

SUPPORTED_FEE_TYPES = frozenset({"DOSSIER_SUBMISSION", "CERTIFICATE_ISSUANCE"})
APPROVED_STATUSES = (
    FeePolicyStatus.SCHEDULED,
    FeePolicyStatus.ACTIVE,
    FeePolicyStatus.EXPIRED,
)


@dataclass(frozen=True, slots=True)
class FeePolicyView:
    id: UUID
    fee_type: str
    dossier_type_id: UUID | None
    version_no: int
    amount_minor: int
    currency: str
    display_name: str
    reason: str
    starts_at: datetime
    ends_at: datetime | None
    status: FeePolicyStatus
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None


@dataclass(frozen=True, slots=True)
class FeeWaiverView:
    id: UUID
    dossier_id: UUID
    fee_type: str
    amount_minor: int
    currency: str
    reason: str
    status: FeeWaiverStatus
    requested_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    redeemed_at: datetime | None
    expires_at: datetime


class FeePolicyService:
    """Versioned, effective-time fee policies with serialized approvals."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(UTC))
        self._audit = AuditService(session)

    def current_time(self) -> datetime:
        return self._aware(self._clock())

    async def create_draft(
        self,
        *,
        actor_user_id: UUID,
        fee_type: str,
        dossier_type_id: UUID | None,
        amount_minor: int,
        starts_at: datetime,
        ends_at: datetime | None,
        reason: str,
        display_name: str | None = None,
    ) -> FeePolicyView:
        normalized_type = fee_type.strip().upper()
        normalized_reason = reason.strip()
        starts = self._aware(starts_at)
        ends = self._aware(ends_at) if ends_at is not None else None
        now = self.current_time()
        if normalized_type not in SUPPORTED_FEE_TYPES:
            raise PriceCatalogConflictError("Unsupported dossier fee type.")
        if normalized_type == "DOSSIER_SUBMISSION" and dossier_type_id is not None:
            raise PriceCatalogConflictError(
                "Submission fee policies must apply to every dossier type."
            )
        if normalized_type != "DOSSIER_SUBMISSION" and dossier_type_id is None:
            raise PriceCatalogConflictError(
                "This fee type requires a dossier type scope."
            )
        if amount_minor <= 0 or amount_minor > 10**12:
            raise PriceCatalogConflictError(
                "Fee amount must be a positive VND integer."
            )
        if starts < now or (ends is not None and ends <= starts):
            raise PriceCatalogConflictError("Fee policy interval is invalid.")
        if not normalized_reason or len(normalized_reason) > 1000:
            raise PriceCatalogConflictError("A policy reason is required.")
        label = (display_name or normalized_type.replace("_", " ").title()).strip()
        if not label or len(label) > 255:
            raise PriceCatalogConflictError("Fee policy name is invalid.")

        async with self._session.begin():
            await self._lock_scope(normalized_type, dossier_type_id)
            version_no = (
                int(
                    await self._session.scalar(
                        select(func.coalesce(func.max(FeePolicy.version_no), 0)).where(
                            FeePolicy.fee_type == normalized_type,
                            FeePolicy.dossier_type_id.is_(None)
                            if dossier_type_id is None
                            else FeePolicy.dossier_type_id == dossier_type_id,
                        )
                    )
                    or 0
                )
                + 1
            )
            policy = FeePolicy(
                id=uuid4(),
                fee_type=normalized_type,
                dossier_type_id=dossier_type_id,
                version_no=version_no,
                amount_minor=amount_minor,
                currency="VND",
                display_name=label,
                reason=normalized_reason,
                starts_at=starts,
                ends_at=ends,
                status=FeePolicyStatus.DRAFT,
                created_by_user_id=actor_user_id,
            )
            self._session.add(policy)
            self._event(
                policy,
                actor_user_id=actor_user_id,
                event_type="CREATED",
                reason=normalized_reason,
                after=self._snapshot(policy),
            )
            self._audit.record(
                actor_user_id=actor_user_id,
                action="billing.fee_policy.created",
                resource_type="fee_policy",
                resource_id=str(policy.id),
                after=self._snapshot(policy),
            )
            await self._session.flush()
            return self._view(policy, now)

    async def apply_submission_fee(
        self,
        *,
        actor_user_id: UUID,
        amount_minor: int,
    ) -> FeePolicyView:
        """Apply a global submission fee from server time, preserving schedules."""
        if amount_minor <= 0 or amount_minor > 10**12:
            raise PriceCatalogConflictError(
                "Fee amount must be a positive VND integer."
            )

        fee_type = "DOSSIER_SUBMISSION"
        reason = "Submission fee applied immediately by an administrator."
        async with self._session.begin():
            await self._lock_scope(fee_type, None)
            # Read the clock after the scope lock so a request queued behind
            # another update cannot apply using a stale pre-lock timestamp.
            now = self.current_time()
            rows = await self._session.scalars(
                select(FeePolicy)
                .where(
                    FeePolicy.fee_type == fee_type,
                    FeePolicy.dossier_type_id.is_(None),
                    FeePolicy.status.in_(APPROVED_STATUSES),
                    FeePolicy.starts_at <= now,
                    or_(FeePolicy.ends_at.is_(None), FeePolicy.ends_at > now),
                )
                .order_by(FeePolicy.starts_at.desc())
                .with_for_update()
            )
            active_policies = tuple(rows)
            if len(active_policies) > 1:
                raise PriceCatalogConflictError(
                    "Multiple submission fee policies are currently effective."
                )
            active = active_policies[0] if active_policies else None
            if active is not None and active.amount_minor == amount_minor:
                return self._view(active, now)

            scheduled_rows = await self._session.scalars(
                select(FeePolicy)
                .where(
                    FeePolicy.fee_type == fee_type,
                    FeePolicy.dossier_type_id.is_(None),
                    FeePolicy.status == FeePolicyStatus.SCHEDULED,
                    FeePolicy.starts_at > now,
                )
                .order_by(FeePolicy.starts_at)
                .with_for_update()
            )
            scheduled_policies = tuple(scheduled_rows)
            next_scheduled = scheduled_policies[0] if scheduled_policies else None
            next_start = (
                self._aware(next_scheduled.starts_at)
                if next_scheduled is not None
                else None
            )

            if active is not None:
                before: dict[str, object] = {
                    "endsAt": self._aware(active.ends_at).isoformat()
                    if active.ends_at is not None
                    else None
                }
                active.ends_at = now
                after: dict[str, object] = {"endsAt": now.isoformat()}
                self._event(
                    active,
                    actor_user_id=actor_user_id,
                    event_type="SUPERSEDED",
                    reason="Superseded by an immediate submission fee update.",
                    before=before,
                    after=after,
                )
                self._audit.record(
                    actor_user_id=actor_user_id,
                    action="billing.fee_policy.superseded",
                    resource_type="fee_policy",
                    resource_id=str(active.id),
                    before=before,
                    after=after,
                )

            version_no = (
                int(
                    await self._session.scalar(
                        select(func.coalesce(func.max(FeePolicy.version_no), 0)).where(
                            FeePolicy.fee_type == fee_type,
                            FeePolicy.dossier_type_id.is_(None),
                        )
                    )
                    or 0
                )
                + 1
            )
            policy = FeePolicy(
                id=uuid4(),
                fee_type=fee_type,
                dossier_type_id=None,
                version_no=version_no,
                amount_minor=amount_minor,
                currency="VND",
                display_name="Submission fee",
                reason=reason,
                starts_at=now,
                ends_at=next_start,
                status=FeePolicyStatus.DRAFT,
                created_by_user_id=actor_user_id,
            )
            self._session.add(policy)
            self._event(
                policy,
                actor_user_id=actor_user_id,
                event_type="CREATED",
                reason=reason,
                after=self._snapshot(policy),
            )
            self._audit.record(
                actor_user_id=actor_user_id,
                action="billing.fee_policy.created",
                resource_type="fee_policy",
                resource_id=str(policy.id),
                after=self._snapshot(policy),
            )
            policy.status = FeePolicyStatus.ACTIVE
            policy.approved_by_user_id = actor_user_id
            policy.approved_at = now
            self._event(
                policy,
                actor_user_id=actor_user_id,
                event_type="APPROVED",
                reason=reason,
                after=self._snapshot(policy),
            )
            self._audit.record(
                actor_user_id=actor_user_id,
                action="billing.fee_policy.approved",
                resource_type="fee_policy",
                resource_id=str(policy.id),
                after=self._snapshot(policy),
            )
            await self._session.flush()
            return self._view(policy, now)

    async def approve(
        self,
        policy_id: UUID,
        *,
        actor_user_id: UUID,
        confirm_activation: bool = False,
    ) -> FeePolicyView:
        now = self.current_time()
        async with self._session.begin():
            policy = await self._policy(policy_id)
            await self._lock_scope(policy.fee_type, policy.dossier_type_id)
            policy = await self._policy(policy_id, for_update=True)
            if policy.status is not FeePolicyStatus.DRAFT:
                raise PriceCatalogConflictError("Only a draft policy can be approved.")
            is_submission_policy = policy.fee_type == "DOSSIER_SUBMISSION"
            if is_submission_policy and not confirm_activation:
                raise PriceCatalogConflictError(
                    "Admin confirmation is required to activate a submission "
                    "fee policy.",
                    code="FEE_POLICY_CONFIRMATION_REQUIRED",
                )
            if policy.created_by_user_id == actor_user_id and not (
                is_submission_policy and confirm_activation
            ):
                raise PriceCatalogConflictError(
                    "A different approver must approve the fee policy."
                )
            if self._aware(policy.starts_at) < now:
                raise PriceCatalogConflictError(
                    "Fee policies cannot take effect retroactively."
                )
            overlap_filters = [
                FeePolicy.fee_type == policy.fee_type,
                FeePolicy.dossier_type_id.is_(None)
                if policy.dossier_type_id is None
                else FeePolicy.dossier_type_id == policy.dossier_type_id,
                FeePolicy.status.in_(APPROVED_STATUSES),
                or_(FeePolicy.ends_at.is_(None), FeePolicy.ends_at > policy.starts_at),
            ]
            if policy.ends_at is not None:
                overlap_filters.append(FeePolicy.starts_at < policy.ends_at)
            rows = await self._session.scalars(
                select(FeePolicy).where(*overlap_filters).with_for_update()
            )
            overlaps = tuple(rows)
            for existing in overlaps:
                if (
                    self._aware(existing.starts_at) < self._aware(policy.starts_at)
                    and existing.ends_at is None
                ):
                    before: dict[str, object] = {"endsAt": None}
                    existing.ends_at = policy.starts_at
                    self._event(
                        existing,
                        actor_user_id=actor_user_id,
                        event_type="SUPERSEDED",
                        reason=f"Superseded by policy version {policy.version_no}.",
                        before=before,
                        after={"endsAt": policy.starts_at.isoformat()},
                    )
                    self._audit.record(
                        actor_user_id=actor_user_id,
                        action="billing.fee_policy.superseded",
                        resource_type="fee_policy",
                        resource_id=str(existing.id),
                        before=before,
                        after={"endsAt": policy.starts_at.isoformat()},
                    )
                else:
                    raise PriceCatalogConflictError(
                        "Approved fee policies overlap for this fee scope."
                    )
            policy.status = (
                FeePolicyStatus.SCHEDULED
                if self._aware(policy.starts_at) > now
                else FeePolicyStatus.ACTIVE
            )
            policy.approved_by_user_id = actor_user_id
            policy.approved_at = now
            approval_snapshot = self._snapshot(policy)
            if is_submission_policy:
                approval_snapshot["activationConfirmed"] = confirm_activation
                approval_snapshot["activatedByCreator"] = (
                    policy.created_by_user_id == actor_user_id
                )
            self._event(
                policy,
                actor_user_id=actor_user_id,
                event_type="APPROVED",
                reason=policy.reason,
                after=approval_snapshot,
            )
            self._audit.record(
                actor_user_id=actor_user_id,
                action="billing.fee_policy.approved",
                resource_type="fee_policy",
                resource_id=str(policy.id),
                after=approval_snapshot,
            )
            await self._session.flush()
            return self._view(policy, now)

    async def cancel(
        self, policy_id: UUID, *, actor_user_id: UUID, reason: str
    ) -> FeePolicyView:
        now = self.current_time()
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise PriceCatalogConflictError("A cancellation reason is required.")
        async with self._session.begin():
            policy = await self._policy(policy_id, for_update=True)
            if policy.status not in {FeePolicyStatus.DRAFT, FeePolicyStatus.SCHEDULED}:
                raise PriceCatalogConflictError(
                    "Only draft or future fee policies can be cancelled."
                )
            before = self._snapshot(policy)
            policy.status = FeePolicyStatus.CANCELLED
            self._event(
                policy,
                actor_user_id=actor_user_id,
                event_type="CANCELLED",
                reason=normalized_reason,
                before=before,
                after=self._snapshot(policy),
            )
            self._audit.record(
                actor_user_id=actor_user_id,
                action="billing.fee_policy.cancelled",
                resource_type="fee_policy",
                resource_id=str(policy.id),
                before=before,
                after=self._snapshot(policy),
            )
            await self._session.flush()
            return self._view(policy, now)

    async def resolve(
        self, *, fee_type: str, dossier_type_id: UUID | None, at: datetime
    ) -> FeePolicyView | None:
        instant = self._aware(at)
        normalized_type = fee_type.strip().upper()
        await self._lock_scope(normalized_type, dossier_type_id)
        matches = await self._session.scalars(
            select(FeePolicy)
            .where(
                FeePolicy.fee_type == normalized_type,
                FeePolicy.dossier_type_id.is_(None)
                if dossier_type_id is None
                else FeePolicy.dossier_type_id == dossier_type_id,
                FeePolicy.status.in_(APPROVED_STATUSES),
                FeePolicy.starts_at <= instant,
                or_(FeePolicy.ends_at.is_(None), FeePolicy.ends_at > instant),
            )
            .limit(2)
        )
        policies = tuple(matches)
        if len(policies) > 1:
            raise PriceCatalogConflictError(
                "Multiple approved fee policies are effective for this scope."
            )
        return self._view(policies[0], instant) if policies else None

    async def get_policy(self, policy_id: UUID, *, at: datetime) -> FeePolicyView:
        policy = await self._policy(policy_id)
        return self._view(policy, self._aware(at))

    async def list_policies(
        self, *, at: datetime, offset: int = 0, limit: int = 50
    ) -> tuple[FeePolicyView, ...]:
        if offset < 0 or not 1 <= limit <= 100:
            raise PriceCatalogConflictError("Invalid fee policy pagination.")
        rows = await self._session.scalars(
            select(FeePolicy)
            .order_by(FeePolicy.created_at.desc(), FeePolicy.id.desc())
            .offset(offset)
            .limit(limit)
        )
        instant = self._aware(at)
        return tuple(self._view(row, instant) for row in rows)

    async def request_waiver(
        self,
        *,
        dossier_id: UUID,
        fee_type: str,
        amount_minor: int,
        reason: str,
        actor_user_id: UUID,
        expires_at: datetime | None = None,
    ) -> FeeWaiverView:
        normalized_type = fee_type.strip().upper()
        normalized_reason = reason.strip()
        now = self.current_time()
        expiry = (
            self._aware(expires_at)
            if expires_at is not None
            else now + timedelta(days=30)
        )
        if normalized_type not in SUPPORTED_FEE_TYPES:
            raise PriceCatalogConflictError("Unsupported dossier fee type.")
        if amount_minor <= 0 or not normalized_reason or len(normalized_reason) > 1000:
            raise PriceCatalogConflictError("Waiver amount and reason are required.")
        if expiry <= now or expiry > now + timedelta(days=90):
            raise PriceCatalogConflictError("Waiver expiry must be within 90 days.")
        async with self._session.begin():
            dossier = await self._session.scalar(
                select(Dossier).where(Dossier.id == dossier_id).with_for_update()
            )
            if dossier is None:
                raise PriceCatalogConflictError("Billable dossier was not found.")
            policy_scope_id = (
                None
                if normalized_type == "DOSSIER_SUBMISSION"
                else dossier.dossier_type_id
            )
            if policy_scope_id is None and normalized_type != "DOSSIER_SUBMISSION":
                raise PriceCatalogConflictError("Billable dossier was not found.")
            policy = await self.resolve(
                fee_type=normalized_type,
                dossier_type_id=policy_scope_id,
                at=now,
            )
            if policy is None or amount_minor > policy.amount_minor:
                raise PriceCatalogConflictError(
                    "Waiver amount exceeds the current fee policy."
                )
            waiver = FeeWaiver(
                id=uuid4(),
                dossier_id=dossier.id,
                fee_type=normalized_type,
                amount_minor=amount_minor,
                currency="VND",
                reason=normalized_reason,
                status=FeeWaiverStatus.REQUESTED,
                requested_by_user_id=actor_user_id,
                expires_at=expiry,
            )
            self._session.add(waiver)
            self._audit.record(
                actor_user_id=actor_user_id,
                action="billing.fee_waiver.requested",
                resource_type="fee_waiver",
                resource_id=str(waiver.id),
                after=self._waiver_snapshot(waiver),
            )
            await self._session.flush()
            return self._waiver_view(waiver, now)

    async def grant_submission_waiver(
        self,
        *,
        dossier_id: UUID,
        reason: str,
        actor_user_id: UUID,
    ) -> FeeWaiverView:
        """Record an administrator's direct, full submission-fee waiver."""
        normalized_reason = reason.strip()
        now = self.current_time()
        if not normalized_reason or len(normalized_reason) > 1000:
            raise PriceCatalogConflictError("A waiver reason is required.")

        async with self._session.begin():
            dossier = await self._session.scalar(
                select(Dossier)
                .where(Dossier.id == dossier_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if dossier is None:
                raise PriceCatalogConflictError("Billable dossier was not found.")
            if dossier.status not in {
                DossierStatus.DRAFT,
                DossierStatus.NEEDS_SUPPLEMENT,
            }:
                raise PriceCatalogConflictError(
                    "A submission fee can only be waived before submission."
                )
            if (
                dossier.submission_fee_paid_at is not None
                or dossier.submission_fee_waived_at is not None
            ):
                raise PriceCatalogConflictError(
                    "A settled submission fee cannot be waived."
                )

            obligation = await self._session.scalar(
                select(FeeObligation)
                .where(
                    FeeObligation.dossier_id == dossier.id,
                    FeeObligation.fee_type == "DOSSIER_SUBMISSION",
                )
                .with_for_update()
            )
            if obligation is not None and obligation.status in {
                FeeObligationStatus.PAID,
                FeeObligationStatus.WAIVED,
            }:
                raise PriceCatalogConflictError(
                    "A settled submission fee cannot be waived."
                )

            if dossier.submission_fee_policy_mode == "DYNAMIC":
                policy = await self.resolve(
                    fee_type="DOSSIER_SUBMISSION",
                    dossier_type_id=None,
                    at=now,
                )
                if policy is None:
                    raise PriceCatalogConflictError(
                        "No approved submission fee policy is currently effective."
                    )
                amount_minor = policy.amount_minor
            else:
                snapshot = dossier.submission_fee_snapshot or {}
                snapshot_amount = snapshot.get("grossAmountMinor")
                if snapshot_amount is None:
                    snapshot_amount = snapshot.get("amountMinor")
                if not isinstance(snapshot_amount, int) or snapshot_amount <= 0:
                    raise PriceCatalogConflictError(
                        "The dossier has no fixed submission fee to waive."
                    )
                amount_minor = snapshot_amount

            waiver = await self._session.scalar(
                select(FeeWaiver)
                .where(
                    FeeWaiver.dossier_id == dossier.id,
                    FeeWaiver.fee_type == "DOSSIER_SUBMISSION",
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            before = self._waiver_snapshot(waiver) if waiver is not None else None
            if waiver is None:
                waiver = FeeWaiver(
                    id=uuid4(),
                    dossier_id=dossier.id,
                    fee_type="DOSSIER_SUBMISSION",
                    amount_minor=amount_minor,
                    currency="VND",
                    reason=normalized_reason,
                    status=FeeWaiverStatus.APPROVED,
                    requested_by_user_id=actor_user_id,
                    approved_by_user_id=actor_user_id,
                    approved_at=now,
                    expires_at=now + timedelta(days=30),
                )
                self._session.add(waiver)
            elif waiver.status is FeeWaiverStatus.REQUESTED:
                waiver.amount_minor = amount_minor
                waiver.reason = normalized_reason
                waiver.status = FeeWaiverStatus.APPROVED
                waiver.requested_by_user_id = actor_user_id
                waiver.approved_by_user_id = actor_user_id
                waiver.approved_at = now
                waiver.expires_at = now + timedelta(days=30)
            else:
                raise PriceCatalogConflictError(
                    "A waiver decision already exists for this dossier."
                )

            self._audit.record(
                actor_user_id=actor_user_id,
                action="billing.fee_waiver.granted",
                resource_type="fee_waiver",
                resource_id=str(waiver.id),
                before=before,
                after={
                    **self._waiver_snapshot(waiver),
                    "grantReason": normalized_reason,
                    "grossFeeMinor": amount_minor,
                },
            )
            await self._session.flush()
            return self._waiver_view(waiver, now)

    async def decide_waiver(
        self,
        waiver_id: UUID,
        *,
        actor_user_id: UUID,
        approve: bool,
        reason: str | None = None,
    ) -> FeeWaiverView:
        now = self.current_time()
        async with self._session.begin():
            waiver = await self._session.scalar(
                select(FeeWaiver)
                .where(FeeWaiver.id == waiver_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if waiver is None:
                raise PriceCatalogConflictError("Fee waiver was not found.")
            if waiver.status is not FeeWaiverStatus.REQUESTED:
                raise PriceCatalogConflictError(
                    "Fee waiver is no longer awaiting approval."
                )
            if waiver.requested_by_user_id == actor_user_id:
                raise PriceCatalogConflictError(
                    "A different approver must decide the fee waiver."
                )
            decision_reason = (reason or waiver.reason).strip()
            if not decision_reason:
                raise PriceCatalogConflictError("A waiver decision reason is required.")
            waiver.status = (
                FeeWaiverStatus.APPROVED if approve else FeeWaiverStatus.REJECTED
            )
            waiver.approved_by_user_id = actor_user_id
            waiver.approved_at = now
            self._audit.record(
                actor_user_id=actor_user_id,
                action=(
                    "billing.fee_waiver.approved"
                    if approve
                    else "billing.fee_waiver.rejected"
                ),
                resource_type="fee_waiver",
                resource_id=str(waiver.id),
                after={
                    **self._waiver_snapshot(waiver),
                    "decisionReason": decision_reason,
                },
            )
            await self._session.flush()
            return self._waiver_view(waiver, now)

    async def apply_approved_waiver(
        self,
        *,
        dossier_id: UUID,
        fee_type: str,
        gross_amount_minor: int,
        actor_user_id: UUID,
    ) -> int:
        now = self.current_time()
        waiver = await self._session.scalar(
            select(FeeWaiver)
            .where(
                FeeWaiver.dossier_id == dossier_id,
                FeeWaiver.fee_type == fee_type,
                FeeWaiver.status == FeeWaiverStatus.APPROVED,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if waiver is None:
            return 0
        if self._aware(waiver.expires_at) <= now:
            before = self._waiver_snapshot(waiver)
            waiver.status = FeeWaiverStatus.EXPIRED
            self._audit.record(
                actor_user_id=actor_user_id,
                action="billing.fee_waiver.expired",
                resource_type="fee_waiver",
                resource_id=str(waiver.id),
                before=before,
                after=self._waiver_snapshot(waiver),
            )
            return 0
        if waiver.amount_minor > gross_amount_minor:
            raise PriceCatalogConflictError(
                "The approved waiver exceeds the current fee; "
                "review it before submission."
            )
        waiver.status = FeeWaiverStatus.REDEEMED
        waiver.redeemed_at = now
        self._audit.record(
            actor_user_id=actor_user_id,
            action="billing.fee_waiver.redeemed",
            resource_type="fee_waiver",
            resource_id=str(waiver.id),
            after=self._waiver_snapshot(waiver),
        )
        return waiver.amount_minor

    async def list_waivers(
        self, *, offset: int = 0, limit: int = 50
    ) -> tuple[FeeWaiverView, ...]:
        if offset < 0 or not 1 <= limit <= 100:
            raise PriceCatalogConflictError("Invalid waiver pagination.")
        rows = await self._session.scalars(
            select(FeeWaiver)
            .order_by(FeeWaiver.created_at.desc(), FeeWaiver.id.desc())
            .offset(offset)
            .limit(limit)
        )
        now = self.current_time()
        return tuple(self._waiver_view(row, now) for row in rows)

    async def _policy(self, policy_id: UUID, *, for_update: bool = False) -> FeePolicy:
        statement = select(FeePolicy).where(FeePolicy.id == policy_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        policy = await self._session.scalar(statement)
        if policy is None:
            raise PriceCatalogConflictError("Fee policy was not found.")
        return policy

    async def _lock_scope(self, fee_type: str, dossier_type_id: UUID | None) -> None:
        if (
            self._session.bind is not None
            and self._session.bind.dialect.name == "postgresql"
        ):
            scope_id = str(dossier_type_id) if dossier_type_id is not None else "GLOBAL"
            scope = f"{fee_type}:{scope_id}"
            await self._session.execute(
                select(func.pg_advisory_xact_lock(func.hashtextextended(scope, 0)))
            )

    def _event(
        self,
        policy: FeePolicy,
        *,
        actor_user_id: UUID,
        event_type: str,
        reason: str,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            FeePolicyEvent(
                id=uuid4(),
                policy_id=policy.id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                before_json=before,
                after_json=after,
                reason=reason,
                created_at=self._aware(self._clock()),
            )
        )

    @classmethod
    def _view(cls, policy: FeePolicy, at: datetime) -> FeePolicyView:
        status = policy.status
        if status in APPROVED_STATUSES:
            now = cls._aware(at)
            starts = cls._aware(policy.starts_at)
            ends = cls._aware(policy.ends_at) if policy.ends_at is not None else None
            status = (
                FeePolicyStatus.SCHEDULED
                if now < starts
                else FeePolicyStatus.EXPIRED
                if ends is not None and now >= ends
                else FeePolicyStatus.ACTIVE
            )
        return FeePolicyView(
            id=policy.id,
            fee_type=policy.fee_type,
            dossier_type_id=policy.dossier_type_id,
            version_no=policy.version_no,
            amount_minor=policy.amount_minor,
            currency=policy.currency,
            display_name=policy.display_name,
            reason=policy.reason,
            starts_at=cls._aware(policy.starts_at),
            ends_at=cls._aware(policy.ends_at) if policy.ends_at is not None else None,
            status=status,
            created_by_user_id=policy.created_by_user_id,
            approved_by_user_id=policy.approved_by_user_id,
            approved_at=cls._aware(policy.approved_at)
            if policy.approved_at is not None
            else None,
        )

    @classmethod
    def _waiver_view(cls, waiver: FeeWaiver, at: datetime) -> FeeWaiverView:
        status = waiver.status
        if status is FeeWaiverStatus.APPROVED and cls._aware(waiver.expires_at) <= at:
            status = FeeWaiverStatus.EXPIRED
        return FeeWaiverView(
            id=waiver.id,
            dossier_id=waiver.dossier_id,
            fee_type=waiver.fee_type,
            amount_minor=waiver.amount_minor,
            currency=waiver.currency,
            reason=waiver.reason,
            status=status,
            requested_by_user_id=waiver.requested_by_user_id,
            approved_by_user_id=waiver.approved_by_user_id,
            approved_at=cls._aware(waiver.approved_at)
            if waiver.approved_at is not None
            else None,
            redeemed_at=cls._aware(waiver.redeemed_at)
            if waiver.redeemed_at is not None
            else None,
            expires_at=cls._aware(waiver.expires_at),
        )

    @staticmethod
    def _snapshot(policy: FeePolicy) -> dict[str, object]:
        return {
            "feeType": policy.fee_type,
            "dossierTypeId": str(policy.dossier_type_id)
            if policy.dossier_type_id is not None
            else None,
            "versionNo": policy.version_no,
            "amountMinor": policy.amount_minor,
            "currency": policy.currency,
            "startsAt": FeePolicyService._aware(policy.starts_at).isoformat(),
            "endsAt": FeePolicyService._aware(policy.ends_at).isoformat()
            if policy.ends_at is not None
            else None,
            "status": policy.status.value,
        }

    @staticmethod
    def _waiver_snapshot(waiver: FeeWaiver) -> dict[str, object]:
        return {
            "dossierId": str(waiver.dossier_id),
            "feeType": waiver.fee_type,
            "amountMinor": waiver.amount_minor,
            "currency": waiver.currency,
            "status": waiver.status.value,
            "requestedByUserId": str(waiver.requested_by_user_id),
            "approvedByUserId": str(waiver.approved_by_user_id)
            if waiver.approved_by_user_id
            else None,
            "expiresAt": FeePolicyService._aware(waiver.expires_at).isoformat(),
        }

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
