from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.events.models import (
    CommunityEvent,
    CommunityEventRegistration,
    MembershipEventEntitlementPolicy,
    MembershipEventEntitlementUsage,
)
from app.modules.memberships.cycle import active_membership_cycle
from app.modules.memberships.models import MembershipDiamondApplication, UserMembership
from app.modules.notifications.models import Notification

TIERS = {"MEMBER": 0, "SILVER": 1, "COMPANION": 2, "PRESTIGE": 3}
ENTITLEMENTS = {"TALK", "CONNECT", "CIRCLE"}
_EVENT_ADMIN = PolicyRequirement(permission="memberships.manage")


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _problem(
    code: str,
    message: str,
    status_code: int,
    *,
    details: dict[str, object] | None = None,
) -> DomainError:
    return DomainError(
        code=code, message=message, status_code=status_code, details=details
    )


class CommunityEventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            _EVENT_ADMIN,
            lambda: _problem("FORBIDDEN", "Event administration is forbidden.", 403),
        )

    @staticmethod
    def _validate_fields(
        fields: dict[str, object], *, creating: bool
    ) -> dict[str, object]:
        allowed = {
            "title",
            "description",
            "starts_at",
            "ends_at",
            "registration_opens_at",
            "priority_tier",
            "priority_opens_at",
            "location",
            "required_tier",
            "capacity",
            "ticket_price_minor",
            "cancellation_cutoff_at",
            "included_entitlement",
            "entitlement_quota",
            "requires_diamond_approval",
        }
        if not fields or fields.keys() - allowed:
            raise _problem("INVALID_EVENT", "Event fields are invalid.", 422)
        clean = dict(fields)
        for name, max_length in (
            ("title", 200),
            ("description", 20000),
            ("location", 300),
        ):
            if name in clean:
                value = clean[name]
                if (
                    not isinstance(value, str)
                    or not value.strip()
                    or len(value.strip()) > max_length
                ):
                    raise _problem("INVALID_EVENT", f"{name} is invalid.", 422)
                clean[name] = value.strip()
        if "required_tier" in clean and clean["required_tier"] not in TIERS:
            raise _problem("INVALID_EVENT", "required_tier is invalid.", 422)
        if "priority_tier" in clean and clean["priority_tier"] not in {
            None,
            "COMPANION",
            "PRESTIGE",
        }:
            raise _problem("INVALID_EVENT", "priority_tier is invalid.", 422)
        if "capacity" in clean and (
            type(clean["capacity"]) is not int or clean["capacity"] < 1
        ):
            raise _problem("INVALID_EVENT", "capacity must be positive.", 422)
        if "ticket_price_minor" in clean and (
            type(clean["ticket_price_minor"]) is not int
            or not 0 <= clean["ticket_price_minor"] <= 1_000_000_000
        ):
            raise _problem("INVALID_EVENT", "ticket_price_minor is invalid.", 422)
        for name in (
            "starts_at",
            "ends_at",
            "registration_opens_at",
            "priority_opens_at",
            "cancellation_cutoff_at",
        ):
            if name in clean and clean[name] is not None:
                value = clean[name]
                if not isinstance(value, datetime) or value.tzinfo is None:
                    raise _problem(
                        "INVALID_EVENT", f"{name} must include a timezone.", 422
                    )
                clean[name] = _utc(value)
        if (
            "included_entitlement" in clean
            and clean["included_entitlement"] is not None
        ):
            if clean["included_entitlement"] not in ENTITLEMENTS:
                raise _problem("INVALID_EVENT", "included_entitlement is invalid.", 422)
        if "entitlement_quota" in clean and clean["entitlement_quota"] is not None:
            if (
                type(clean["entitlement_quota"]) is not int
                or clean["entitlement_quota"] < 1
            ):
                raise _problem(
                    "INVALID_EVENT", "entitlement_quota must be positive.", 422
                )
        if (
            "requires_diamond_approval" in clean
            and type(clean["requires_diamond_approval"]) is not bool
        ):
            raise _problem(
                "INVALID_EVENT", "requires_diamond_approval must be boolean.", 422
            )
        if creating:
            required = allowed - {
                "registration_opens_at",
                "priority_tier",
                "priority_opens_at",
                "cancellation_cutoff_at",
                "included_entitlement",
                "entitlement_quota",
                "requires_diamond_approval",
            }
            if required - clean.keys():
                raise _problem(
                    "INVALID_EVENT", "Required event fields are missing.", 422
                )
            clean.setdefault("cancellation_cutoff_at", None)
            clean.setdefault("registration_opens_at", None)
            clean.setdefault("priority_tier", None)
            clean.setdefault("priority_opens_at", None)
            clean.setdefault("included_entitlement", None)
            clean.setdefault("entitlement_quota", None)
            clean.setdefault("requires_diamond_approval", False)
        final_entitlement = clean.get("included_entitlement")
        final_quota = clean.get("entitlement_quota")
        if creating and (final_entitlement is None) != (final_quota is None):
            raise _problem(
                "INVALID_EVENT",
                "included_entitlement and entitlement_quota must be "
                "configured together.",
                422,
            )
        return clean

    async def create(
        self, principal: AuthPrincipal, **fields: object
    ) -> CommunityEvent:
        self._require_admin(principal)
        clean = self._validate_fields(fields, creating=True)
        starts_at = clean["starts_at"]
        ends_at = clean["ends_at"]
        cutoff = clean["cancellation_cutoff_at"]
        if not isinstance(starts_at, datetime) or not isinstance(ends_at, datetime):
            raise _problem("INVALID_EVENT", "Event dates are invalid.", 422)
        if _utc(ends_at) <= _utc(starts_at) or (
            cutoff is not None
            and (not isinstance(cutoff, datetime) or _utc(cutoff) > _utc(starts_at))
        ):
            raise _problem("INVALID_EVENT", "Event dates are inconsistent.", 422)
        self._validate_registration_windows(
            required_tier=clean["required_tier"],
            registration_opens_at=clean["registration_opens_at"],
            priority_tier=clean["priority_tier"],
            priority_opens_at=clean["priority_opens_at"],
            starts_at=starts_at,
        )
        is_circle = clean["included_entitlement"] == "CIRCLE"
        if (clean["requires_diamond_approval"] or is_circle) and clean[
            "required_tier"
        ] != "PRESTIGE":
            raise _problem(
                "INVALID_EVENT", "Diamond Circle events require PRESTIGE access.", 422
            )
        if is_circle and not clean["requires_diamond_approval"]:
            raise _problem(
                "INVALID_EVENT",
                "Circle events require an approved Diamond application.",
                422,
            )
        async with self.session.begin():
            event = CommunityEvent(
                **clean,
                created_by_user_id=principal.user_id,
                status="DRAFT",
                confirmed_count=0,
            )
            self.session.add(event)
            await self.session.flush()
            self._audit(
                principal,
                "community.event.created",
                event,
                after={"status": event.status, "title": event.title},
            )
            await self.session.refresh(event)
            return event

    async def update(
        self,
        principal: AuthPrincipal,
        event_id: UUID,
        **fields: object,
    ) -> CommunityEvent:
        self._require_admin(principal)
        clean = self._validate_fields(fields, creating=False)
        async with self.session.begin():
            event = await self._event(event_id, lock=True)
            if event.status == "CANCELLED":
                raise _problem(
                    "EVENT_CANCELLED", "Cancelled events cannot be edited.", 409
                )
            proposed = {
                column: getattr(event, column)
                for column in (
                    "starts_at",
                    "ends_at",
                    "registration_opens_at",
                    "priority_tier",
                    "priority_opens_at",
                    "cancellation_cutoff_at",
                    "required_tier",
                    "capacity",
                    "included_entitlement",
                    "entitlement_quota",
                    "requires_diamond_approval",
                )
            }
            proposed.update(clean)
            proposed_starts = proposed["starts_at"]
            proposed_ends = proposed["ends_at"]
            if not isinstance(proposed_starts, datetime) or not isinstance(
                proposed_ends, datetime
            ):
                raise _problem("INVALID_EVENT", "Event dates are invalid.", 422)
            if _utc(proposed_ends) <= _utc(proposed_starts):
                raise _problem("INVALID_EVENT", "Event dates are inconsistent.", 422)
            self._validate_registration_windows(
                required_tier=proposed["required_tier"],
                registration_opens_at=proposed["registration_opens_at"],
                priority_tier=proposed["priority_tier"],
                priority_opens_at=proposed["priority_opens_at"],
                starts_at=proposed_starts,
            )
            cutoff = proposed["cancellation_cutoff_at"]
            if cutoff is not None and (
                not isinstance(cutoff, datetime) or _utc(cutoff) > _utc(proposed_starts)
            ):
                raise _problem(
                    "INVALID_EVENT", "Cancellation cutoff must precede the event.", 422
                )
            is_circle = proposed["included_entitlement"] == "CIRCLE"
            if (proposed["requires_diamond_approval"] or is_circle) and proposed[
                "required_tier"
            ] != "PRESTIGE":
                raise _problem(
                    "INVALID_EVENT",
                    "Diamond Circle events require PRESTIGE access.",
                    422,
                )
            if is_circle and not proposed["requires_diamond_approval"]:
                raise _problem(
                    "INVALID_EVENT",
                    "Circle events require an approved Diamond application.",
                    422,
                )
            if (proposed["included_entitlement"] is None) != (
                proposed["entitlement_quota"] is None
            ):
                raise _problem(
                    "INVALID_EVENT",
                    "included_entitlement and entitlement_quota must be "
                    "configured together.",
                    422,
                )
            capacity = proposed["capacity"]
            if not isinstance(capacity, int) or capacity < event.confirmed_count:
                raise _problem(
                    "CAPACITY_BELOW_CONFIRMED",
                    "Capacity cannot be lower than confirmed registrations.",
                    409,
                )
            before = {name: getattr(event, name) for name in clean}
            for name, value in clean.items():
                setattr(event, name, value)
            await self.session.flush()
            self._audit(
                principal,
                "community.event.updated",
                event,
                before={key: self._audit_value(value) for key, value in before.items()},
                after={key: self._audit_value(getattr(event, key)) for key in clean},
            )
            await self.session.refresh(event)
            return event

    async def publish(self, principal: AuthPrincipal, event_id: UUID) -> CommunityEvent:
        self._require_admin(principal)
        async with self.session.begin():
            event = await self._event(event_id, lock=True)
            if event.status == "CANCELLED":
                raise _problem(
                    "EVENT_CANCELLED", "Cancelled events cannot be published.", 409
                )
            if event.status != "PUBLISHED":
                event.status = "PUBLISHED"
                await self._notify_eligible_members(event)
                self._audit(
                    principal,
                    "community.event.published",
                    event,
                    after={"status": event.status},
                )
                await self.session.flush()
            await self.session.refresh(event)
            return event

    async def cancel_event(
        self, principal: AuthPrincipal, event_id: UUID
    ) -> CommunityEvent:
        self._require_admin(principal)
        async with self.session.begin():
            event = await self._event(event_id, lock=True)
            if event.status != "CANCELLED":
                event.status = "CANCELLED"
                registrations = list(
                    await self.session.scalars(
                        select(CommunityEventRegistration)
                        .where(CommunityEventRegistration.event_id == event_id)
                        .with_for_update()
                    )
                )
                for registration in registrations:
                    if registration.status in {
                        "CONFIRMED",
                        "WAITLISTED",
                        "PAYMENT_REQUIRED",
                    }:
                        registration.status = "CANCELLED_BY_EVENT"
                        registration.cancelled_at = datetime.now(UTC)
                    if registration.entitlement_units:
                        await self._restore_entitlement(registration)
                event.confirmed_count = 0
                self._audit(
                    principal,
                    "community.event.cancelled",
                    event,
                    after={"status": event.status},
                )
            await self.session.flush()
            await self.session.refresh(event)
            return event

    async def list_public(
        self, *, page: int, page_size: int
    ) -> tuple[list[CommunityEvent], int]:
        now = datetime.now(UTC)
        async with self.session.begin():
            filters = (
                CommunityEvent.status == "PUBLISHED",
                CommunityEvent.starts_at > now,
            )
            total = int(
                await self.session.scalar(
                    select(func.count()).select_from(CommunityEvent).where(*filters)
                )
                or 0
            )
            events = list(
                await self.session.scalars(
                    select(CommunityEvent)
                    .where(*filters)
                    .order_by(CommunityEvent.starts_at, CommunityEvent.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            return events, total

    async def list_admin(
        self, principal: AuthPrincipal, *, page: int, page_size: int
    ) -> tuple[list[CommunityEvent], int]:
        self._require_admin(principal)
        async with self.session.begin():
            total = int(
                await self.session.scalar(
                    select(func.count()).select_from(CommunityEvent)
                )
                or 0
            )
            events = list(
                await self.session.scalars(
                    select(CommunityEvent)
                    .order_by(CommunityEvent.starts_at.desc(), CommunityEvent.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            return events, total

    async def my_registrations(
        self, principal: AuthPrincipal, *, page: int, page_size: int
    ) -> tuple[list[tuple[CommunityEventRegistration, CommunityEvent]], int]:
        async with self.session.begin():
            total = int(
                await self.session.scalar(
                    select(func.count())
                    .select_from(CommunityEventRegistration)
                    .where(CommunityEventRegistration.user_id == principal.user_id)
                )
                or 0
            )
            rows = await self.session.execute(
                select(CommunityEventRegistration, CommunityEvent)
                .join(
                    CommunityEvent,
                    CommunityEvent.id == CommunityEventRegistration.event_id,
                )
                .where(CommunityEventRegistration.user_id == principal.user_id)
                .order_by(
                    CommunityEventRegistration.registered_at.desc(),
                    CommunityEventRegistration.id,
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            return [(registration, event) for registration, event in rows.all()], total

    async def register(
        self, principal: AuthPrincipal, event_id: UUID
    ) -> CommunityEventRegistration:
        async with self.session.begin():
            await self.session.scalar(
                select(User.id).where(User.id == principal.user_id).with_for_update()
            )
            event = await self._event(event_id, lock=True)
            existing = await self.session.scalar(
                select(CommunityEventRegistration)
                .where(
                    CommunityEventRegistration.event_id == event_id,
                    CommunityEventRegistration.user_id == principal.user_id,
                    CommunityEventRegistration.status.in_(("CONFIRMED", "WAITLISTED")),
                )
                .with_for_update()
            )
            if existing is not None:
                return existing
            if event.status != "PUBLISHED" or _utc(event.starts_at) <= datetime.now(
                UTC
            ):
                raise _problem(
                    "EVENT_UNAVAILABLE", "Event is not open for registration.", 409
                )
            access = await self._membership_access(principal.user_id, event)
            if access is None:
                if event.requires_diamond_approval:
                    raise _problem(
                        "DIAMOND_APPROVAL_REQUIRED",
                        "A current Diamond membership and approved application "
                        "are required.",
                        403,
                    )
                raise _problem(
                    "MEMBERSHIP_TIER_REQUIRED", "Membership tier is too low.", 403
                )
            tier, cycle_started_at = access
            now = datetime.now(UTC)
            registration_opens_at = event.registration_opens_at
            priority_opens_at = event.priority_opens_at
            if registration_opens_at is not None and now < _utc(
                registration_opens_at
            ):
                has_priority_access = (
                    event.priority_tier is not None
                    and priority_opens_at is not None
                    and now >= _utc(priority_opens_at)
                    and TIERS[tier] >= TIERS[event.priority_tier]
                )
                if not has_priority_access:
                    raise _problem(
                        "EVENT_REGISTRATION_NOT_OPEN",
                        "Registration has not opened for this membership tier.",
                        409,
                    )
            entitlement_available = await self._has_entitlement(
                principal.user_id, tier, cycle_started_at, event
            )
            if event.included_entitlement is not None and not entitlement_available:
                if event.ticket_price_minor > 0:
                    raise self._payment_required(event)
                raise _problem(
                    "EVENT_ENTITLEMENT_QUOTA_EXHAUSTED",
                    "The included event entitlement quota has been used.",
                    409,
                    details={"entitlement": event.included_entitlement},
                )
            if event.included_entitlement is None and event.ticket_price_minor > 0:
                raise self._payment_required(event)

            can_confirm = await self._claim_seat(event)
            entitlement_units = 0
            entitlement_snapshot = None
            entitlement_cycle_started_at = None
            membership_tier_snapshot = None
            if can_confirm and event.included_entitlement is not None:
                assert cycle_started_at is not None
                assert event.entitlement_quota is not None
                consumed = await self._consume_entitlement(
                    principal.user_id,
                    tier,
                    event.included_entitlement,
                    cycle_started_at,
                    event.entitlement_quota,
                )
                if not consumed:
                    if event.ticket_price_minor > 0:
                        raise self._payment_required(event)
                    raise _problem(
                        "EVENT_ENTITLEMENT_QUOTA_EXHAUSTED",
                        "The included event entitlement quota has been used.",
                        409,
                        details={"entitlement": event.included_entitlement},
                    )
                entitlement_units = event.entitlement_quota
                entitlement_snapshot = event.included_entitlement
                entitlement_cycle_started_at = cycle_started_at
                membership_tier_snapshot = tier
            registration = CommunityEventRegistration(
                event_id=event.id,
                user_id=principal.user_id,
                status="CONFIRMED" if can_confirm else "WAITLISTED",
                entitlement_units=entitlement_units,
                entitlement_snapshot=entitlement_snapshot,
                entitlement_cycle_started_at=entitlement_cycle_started_at,
                membership_tier_snapshot=membership_tier_snapshot,
                registered_at=datetime.now(UTC),
            )
            self.session.add(registration)
            await self.session.flush()
            return registration

    async def cancel_registration(
        self, principal: AuthPrincipal, event_id: UUID
    ) -> CommunityEventRegistration:
        async with self.session.begin():
            event = await self._event(event_id, lock=True)
            registration = await self.session.scalar(
                select(CommunityEventRegistration)
                .where(
                    CommunityEventRegistration.event_id == event_id,
                    CommunityEventRegistration.user_id == principal.user_id,
                )
                .order_by(CommunityEventRegistration.registered_at.desc())
                .limit(1)
                .with_for_update()
            )
            if registration is None:
                raise _problem("REGISTRATION_NOT_FOUND", "Registration not found.", 404)
            if registration.status not in {
                "CONFIRMED",
                "WAITLISTED",
                "PAYMENT_REQUIRED",
            }:
                return registration
            now = datetime.now(UTC)
            if _utc(event.starts_at) <= now:
                raise _problem(
                    "EVENT_ALREADY_STARTED", "Event has already started.", 409
                )
            was_confirmed = registration.status == "CONFIRMED"
            restore_entitlement = registration.entitlement_units > 0 and now <= _utc(
                event.cancellation_cutoff_at or event.starts_at
            )
            if was_confirmed:
                await self._release_seat(event)
            registration.status = (
                "CANCELLED"
                if restore_entitlement or not registration.entitlement_units
                else "CANCELLED_LATE"
            )
            registration.cancelled_at = now
            if restore_entitlement:
                await self._restore_entitlement(registration)
            await self.session.flush()
            if was_confirmed and event.status == "PUBLISHED":
                await self._promote_waitlist(event)
            return registration

    async def _membership_access(
        self, user_id: UUID, event: CommunityEvent
    ) -> tuple[str, datetime | None] | None:
        tier, cycle_started_at = await self._active_membership_cycle(user_id)
        if TIERS.get(tier, -1) < TIERS[event.required_tier]:
            return None
        if event.requires_diamond_approval or event.included_entitlement == "CIRCLE":
            approved = await self.session.scalar(
                select(MembershipDiamondApplication.id)
                .where(
                    MembershipDiamondApplication.user_id == user_id,
                    MembershipDiamondApplication.status == "APPROVED",
                )
                .limit(1)
            )
            if approved is None:
                return None
        return tier, cycle_started_at

    async def _active_membership_cycle(
        self, user_id: UUID
    ) -> tuple[str, datetime | None]:
        return await active_membership_cycle(self.session, user_id)

    @staticmethod
    def _validate_registration_windows(
        *,
        required_tier: object,
        registration_opens_at: object,
        priority_tier: object,
        priority_opens_at: object,
        starts_at: datetime,
    ) -> None:
        if registration_opens_at is not None and (
            not isinstance(registration_opens_at, datetime)
            or _utc(registration_opens_at) >= _utc(starts_at)
        ):
            raise _problem(
                "INVALID_REGISTRATION_WINDOW",
                "Registration must open before the event starts.",
                422,
            )
        if priority_tier is None:
            if priority_opens_at is not None:
                raise _problem(
                    "INVALID_REGISTRATION_WINDOW",
                    "A priority opening time requires a priority tier.",
                    422,
                )
            return
        if (
            priority_tier not in {"COMPANION", "PRESTIGE"}
            or not isinstance(priority_opens_at, datetime)
            or not isinstance(registration_opens_at, datetime)
            or required_tier not in TIERS
            or TIERS[str(priority_tier)] < TIERS[str(required_tier)]
            or _utc(priority_opens_at) >= _utc(registration_opens_at)
            or _utc(priority_opens_at) >= _utc(starts_at)
        ):
            raise _problem(
                "INVALID_REGISTRATION_WINDOW",
                "Priority access must open before general registration and the "
                "event, for an eligible tier.",
                422,
            )

    async def _notify_eligible_members(self, event: CommunityEvent) -> None:
        now = datetime.now(UTC)
        memberships = list(
            await self.session.scalars(
                select(UserMembership)
                .join(User, User.id == UserMembership.user_id)
                .where(
                    User.status == UserStatus.ACTIVE,
                    UserMembership.expires_at > now,
                )
            )
        )
        eligible = [
            membership
            for membership in memberships
            if TIERS.get(membership.tier, -1) >= TIERS[event.required_tier]
        ]
        if event.requires_diamond_approval and eligible:
            approved_ids = set(
                await self.session.scalars(
                    select(MembershipDiamondApplication.user_id).where(
                        MembershipDiamondApplication.user_id.in_(
                            [membership.user_id for membership in eligible]
                        ),
                        MembershipDiamondApplication.status == "APPROVED",
                    )
                )
            )
            eligible = [
                membership
                for membership in eligible
                if membership.tier != "PRESTIGE"
                or membership.user_id in approved_ids
            ]
        self.session.add_all(
            Notification(
                user_id=membership.user_id,
                source_event_id=event.id,
                type="MEMBERSHIP_PROGRAM_AVAILABLE",
                title="Chương trình hội viên mới",
                body=(
                    f"{event.title} đã mở lịch đăng ký phù hợp với hạng hội viên "
                    "của bạn."
                ),
                data_json={"actionPath": "/events", "eventId": str(event.id)},
                created_at=now,
            )
            for membership in eligible
        )

    async def _has_entitlement(
        self,
        user_id: UUID,
        tier: str,
        cycle_started_at: datetime | None,
        event: CommunityEvent,
    ) -> bool:
        if (
            event.included_entitlement is None
            or event.entitlement_quota is None
            or cycle_started_at is None
        ):
            return False
        policy = await self.session.get(
            MembershipEventEntitlementPolicy,
            (tier, event.included_entitlement),
        )
        if policy is None or event.entitlement_quota > policy.quota_count:
            return False
        usage = await self.session.get(
            MembershipEventEntitlementUsage,
            (user_id, tier, event.included_entitlement, cycle_started_at),
        )
        return (
            usage is None
            or usage.used_count + event.entitlement_quota <= policy.quota_count
        )

    async def _consume_entitlement(
        self,
        user_id: UUID,
        tier: str,
        entitlement: str,
        cycle_started_at: datetime,
        units: int,
    ) -> bool:
        policy = await self.session.get(
            MembershipEventEntitlementPolicy, (tier, entitlement)
        )
        if policy is None or units > policy.quota_count:
            return False
        values = {
            "user_id": user_id,
            "tier": tier,
            "entitlement": entitlement,
            "cycle_started_at": cycle_started_at,
            "used_count": units,
        }
        dialect = self.session.get_bind().dialect.name
        insert = (
            sqlite_insert
            if dialect == "sqlite"
            else postgresql_insert
            if dialect == "postgresql"
            else None
        )
        if insert is None:
            raise RuntimeError(f"Unsupported entitlement usage dialect: {dialect}")
        statement: Any = insert(MembershipEventEntitlementUsage).values(**values)
        key_columns = [
            MembershipEventEntitlementUsage.user_id,
            MembershipEventEntitlementUsage.tier,
            MembershipEventEntitlementUsage.entitlement,
            MembershipEventEntitlementUsage.cycle_started_at,
        ]
        statement = statement.on_conflict_do_update(
            index_elements=key_columns,
            set_={"used_count": MembershipEventEntitlementUsage.used_count + units},
            where=(
                MembershipEventEntitlementUsage.used_count + units <= policy.quota_count
            ),
        ).returning(MembershipEventEntitlementUsage.user_id)
        return await self.session.scalar(statement) is not None

    async def _restore_entitlement(
        self, registration: CommunityEventRegistration
    ) -> None:
        units = registration.entitlement_units
        entitlement = registration.entitlement_snapshot
        cycle_started_at = registration.entitlement_cycle_started_at
        tier = registration.membership_tier_snapshot
        if not units or entitlement is None or cycle_started_at is None or tier is None:
            raise _problem(
                "EVENT_ENTITLEMENT_INTEGRITY",
                "Registration entitlement snapshot is incomplete.",
                409,
            )
        restored_user = await self.session.scalar(
            update(MembershipEventEntitlementUsage)
            .where(
                MembershipEventEntitlementUsage.user_id == registration.user_id,
                MembershipEventEntitlementUsage.tier == tier,
                MembershipEventEntitlementUsage.entitlement == entitlement,
                MembershipEventEntitlementUsage.cycle_started_at == cycle_started_at,
                MembershipEventEntitlementUsage.used_count >= units,
            )
            .values(used_count=MembershipEventEntitlementUsage.used_count - units)
            .returning(MembershipEventEntitlementUsage.user_id)
        )
        if restored_user is None:
            raise _problem(
                "EVENT_ENTITLEMENT_INTEGRITY",
                "Registration entitlement usage is inconsistent.",
                409,
            )
        registration.entitlement_units = 0
        registration.entitlement_snapshot = None
        registration.entitlement_cycle_started_at = None
        registration.membership_tier_snapshot = None

    @staticmethod
    def _payment_required(event: CommunityEvent) -> DomainError:
        return _problem(
            "PAYMENT_REQUIRED",
            "Event ticket payment is not available yet.",
            402,
            details={
                "event_id": str(event.id),
                "amount_minor": event.ticket_price_minor,
            },
        )

    async def _claim_seat(self, event: CommunityEvent) -> bool:
        values: dict[str, Any] = {
            "confirmed_count": CommunityEvent.confirmed_count + 1,
        }
        conditions = [
            CommunityEvent.id == event.id,
            CommunityEvent.status == "PUBLISHED",
            CommunityEvent.confirmed_count < CommunityEvent.capacity,
        ]
        claimed_id = await self.session.scalar(
            update(CommunityEvent)
            .where(*conditions)
            .values(**values)
            .returning(CommunityEvent.id)
            .execution_options(synchronize_session=False)
        )
        if claimed_id is not None:
            event.confirmed_count += 1
            return True
        return False

    async def _release_seat(self, event: CommunityEvent) -> None:
        values: dict[str, Any] = {
            "confirmed_count": CommunityEvent.confirmed_count - 1,
        }
        conditions = [
            CommunityEvent.id == event.id,
            CommunityEvent.confirmed_count > 0,
        ]
        released_id = await self.session.scalar(
            update(CommunityEvent)
            .where(*conditions)
            .values(**values)
            .returning(CommunityEvent.id)
            .execution_options(synchronize_session=False)
        )
        if released_id is None:
            raise _problem(
                "EVENT_CAPACITY_INTEGRITY", "Event counters are inconsistent.", 409
            )
        event.confirmed_count -= 1

    async def _promote_waitlist(self, event: CommunityEvent) -> None:
        waiters = list(
            await self.session.scalars(
                select(CommunityEventRegistration)
                .where(
                    CommunityEventRegistration.event_id == event.id,
                    CommunityEventRegistration.status == "WAITLISTED",
                )
                .order_by(
                    CommunityEventRegistration.registered_at,
                    CommunityEventRegistration.id,
                )
                .with_for_update(skip_locked=True)
            )
        )
        for waiter in waiters:
            if event.confirmed_count >= event.capacity:
                return
            access = await self._membership_access(waiter.user_id, event)
            if access is None:
                waiter.status = "INELIGIBLE"
                continue
            tier, cycle_started_at = access
            if event.included_entitlement is None and event.ticket_price_minor > 0:
                waiter.status = "PAYMENT_REQUIRED"
                continue
            if (
                event.included_entitlement is not None
                and not await self._has_entitlement(
                    waiter.user_id, tier, cycle_started_at, event
                )
            ):
                if event.ticket_price_minor > 0:
                    waiter.status = "PAYMENT_REQUIRED"
                else:
                    waiter.status = "INELIGIBLE"
                continue
            if not await self._claim_seat(event):
                return
            if event.included_entitlement is not None:
                if cycle_started_at is None or event.entitlement_quota is None:
                    await self._release_seat(event)
                    waiter.status = "INELIGIBLE"
                    continue
                consumed = await self._consume_entitlement(
                    waiter.user_id,
                    tier,
                    event.included_entitlement,
                    cycle_started_at,
                    event.entitlement_quota,
                )
                if not consumed:
                    await self._release_seat(event)
                    waiter.status = (
                        "PAYMENT_REQUIRED"
                        if event.ticket_price_minor > 0
                        else "INELIGIBLE"
                    )
                    continue
                waiter.entitlement_units = event.entitlement_quota
                waiter.entitlement_snapshot = event.included_entitlement
                waiter.entitlement_cycle_started_at = cycle_started_at
                waiter.membership_tier_snapshot = tier
            waiter.status = "CONFIRMED"
            await self.session.flush()

    async def _event(self, event_id: UUID, *, lock: bool = False) -> CommunityEvent:
        query = select(CommunityEvent).where(CommunityEvent.id == event_id)
        if lock:
            query = query.with_for_update()
        event = await self.session.scalar(query)
        if event is None:
            raise _problem("EVENT_NOT_FOUND", "Event not found.", 404)
        return event

    @staticmethod
    def _audit_value(value: object) -> object:
        if isinstance(value, datetime):
            return _utc(value).isoformat()
        return value

    def _audit(
        self,
        principal: AuthPrincipal,
        action: str,
        event: CommunityEvent,
        *,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
    ) -> None:
        AuditService(self.session).record(
            actor_user_id=principal.user_id,
            action=action,
            resource_type="community_event",
            resource_id=str(event.id),
            before=before,
            after=after,
        )
