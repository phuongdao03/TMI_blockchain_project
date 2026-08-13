import re
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.council.errors import (
    CouncilConflictError,
    CouncilForbiddenError,
    CouncilNotFoundError,
    CouncilValidationError,
)
from app.modules.council.minutes import (
    build_minutes_payload,
    calculate_case_result,
    group_votes,
)
from app.modules.council.models import (
    CouncilCase,
    CouncilCaseConflict,
    CouncilCaseDecision,
    CouncilSession,
    CouncilSessionMember,
    CouncilSessionStatus,
    CouncilVote,
    CouncilVoteChoice,
)
from app.modules.council.repository import CouncilRepository
from app.modules.council.types import (
    CouncilCaseDetailView,
    CouncilCaseResultView,
    CouncilCaseView,
    CouncilConflictView,
    CouncilMemberView,
    CouncilMinutesView,
    CouncilSessionDetailView,
    CouncilSessionListItemView,
    CouncilSessionPage,
    CouncilSessionView,
    CouncilVoteView,
)
from app.modules.dossiers.canonical import snapshot_sha256
from app.modules.dossiers.models import DossierStatus, DossierVersion
from app.modules.dossiers.provenance import version_has_trusted_provenance
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.workflow import DossierWorkflowService
from app.modules.reviews.repository import ReviewRepository

SECRETARY_ROLES = frozenset({"COUNCIL_SECRETARY", "SUPER_ADMIN"})
MEMBER_ROLES = frozenset({"COUNCIL_MEMBER"})
CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,63}$")
DECIDED_EVENT = "council.decided"
DECISION_TARGETS = {
    CouncilCaseDecision.APPROVE: DossierStatus.APPROVED,
    CouncilCaseDecision.REJECT: DossierStatus.REJECTED,
    CouncilCaseDecision.REQUEST_MORE_INFO: DossierStatus.NEEDS_SUPPLEMENT,
}


class CouncilService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        payload_cipher: OutboxPayloadCipher,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._session = session
        self._council = CouncilRepository(session)
        self._dossiers = DossierRepository(session)
        self._reviews = ReviewRepository(session)
        self._workflow = DossierWorkflowService(self._dossiers)
        self._outbox = OutboxRepository(session)
        self._audit_service = AuditService(session)
        self._payload_cipher = payload_cipher
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    async def create_session(
        self,
        principal: AuthPrincipal,
        *,
        code: str,
        title: str,
        scheduled_at: datetime,
        quorum_required: int,
        member_user_ids: tuple[UUID, ...],
    ) -> CouncilSessionView:
        self._require_secretary(principal)
        normalized_code = code.strip().upper()
        normalized_title = title.strip()
        member_ids = self._member_ids(member_user_ids)
        if not CODE_PATTERN.fullmatch(normalized_code):
            raise CouncilValidationError("Council session code is invalid.")
        if not normalized_title or len(normalized_title) > 255:
            raise CouncilValidationError(
                "Council session title must contain between 1 and 255 characters."
            )
        if quorum_required < 1 or quorum_required > len(member_ids):
            raise CouncilValidationError(
                "Quorum must be positive and cannot exceed the member count."
            )
        normalized_schedule = self._utc(scheduled_at)

        try:
            async with self._session.begin():
                for member_id in member_ids:
                    if await self._council.get_active_member(member_id) is None:
                        raise CouncilValidationError(
                            "Every session member must be an active council member."
                        )
                council_session = CouncilSession(
                    id=self._uuid_factory(),
                    code=normalized_code,
                    title=normalized_title,
                    scheduled_at=normalized_schedule,
                    status=CouncilSessionStatus.DRAFT,
                    quorum_required=quorum_required,
                )
                self._council.add_session(council_session)
                for member_id in member_ids:
                    self._council.add_member(
                        CouncilSessionMember(
                            id=self._uuid_factory(),
                            session_id=council_session.id,
                            member_user_id=member_id,
                        )
                    )
                await self._session.flush()
                result = self._session_view(
                    council_session,
                    member_count=len(member_ids),
                    attendance_count=0,
                )
                self._audit(
                    "council.session.created",
                    principal.user_id,
                    "council_session",
                    result.id,
                )
        except IntegrityError as exc:
            raise CouncilConflictError("Council session code already exists.") from exc
        return result

    async def add_case(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
        dossier_id: UUID,
    ) -> CouncilCaseView:
        self._require_secretary(principal)
        try:
            async with self._session.begin():
                council_session = await self._required_session(
                    session_id,
                    for_update=True,
                )
                self._require_draft(council_session)
                dossier = await self._dossiers.get_by_id(
                    dossier_id,
                    for_update=True,
                )
                if dossier is None:
                    raise CouncilNotFoundError("Dossier was not found.")
                if (
                    dossier.status is not DossierStatus.UNDER_REVIEW
                    or dossier.current_version_no < 1
                ):
                    raise CouncilConflictError(
                        "Only a current UNDER_REVIEW dossier can be added."
                    )
                version = await self._dossiers.get_version(
                    dossier.id,
                    dossier.current_version_no,
                )
                if version is None:
                    raise CouncilConflictError(
                        "The current dossier version was not found."
                    )
                (
                    submitted_reviews,
                    unfinished_assignments,
                ) = await self._reviews.get_council_review_gate(version.id)
                if submitted_reviews < 1:
                    raise CouncilConflictError(
                        "At least one complete submitted review is required "
                        "before council consideration."
                    )
                if unfinished_assignments:
                    raise CouncilConflictError(
                        "Every assigned reviewer must submit or declare a "
                        "conflict before council consideration."
                    )
                if await self._council.get_session_case_for_version(
                    council_session.id,
                    version.id,
                ):
                    raise CouncilConflictError(
                        "This dossier version is already in the session."
                    )
                council_case = CouncilCase(
                    id=self._uuid_factory(),
                    session_id=council_session.id,
                    dossier_id=dossier.id,
                    dossier_version_id=version.id,
                )
                self._council.add_case(council_case)
                await self._session.flush()
                result = CouncilCaseView(
                    id=council_case.id,
                    session_id=council_case.session_id,
                    dossier_id=dossier.id,
                    dossier_version_id=version.id,
                    dossier_code=dossier.code,
                    dossier_title=dossier.title,
                    version_no=version.version_no,
                    decision=None,
                )
                self._audit(
                    "council.case.added",
                    principal.user_id,
                    "council_case",
                    result.id,
                )
        except IntegrityError as exc:
            raise CouncilConflictError(
                "This dossier version is already in the session."
            ) from exc
        return result

    async def confirm_attendance(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilMemberView:
        self._require_member(principal)
        async with self._session.begin():
            council_session = await self._required_session(
                session_id,
                for_update=True,
            )
            self._require_draft(council_session)
            membership = await self._council.get_membership(
                session_id,
                principal.user_id,
                for_update=True,
            )
            if membership is None:
                raise CouncilNotFoundError()
            if membership.attendance_confirmed_at is not None:
                raise CouncilConflictError("Attendance is already confirmed.")
            membership.attendance_confirmed_at = self._clock()
            await self._session.flush()
            result = self._member_view(membership)
            self._audit(
                "council.attendance.confirmed",
                principal.user_id,
                "council_session",
                session_id,
            )
        return result

    async def open_session(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilSessionView:
        self._require_secretary(principal)
        async with self._session.begin():
            council_session = await self._required_session(
                session_id,
                for_update=True,
            )
            self._require_draft(council_session)
            cases = await self._council.list_cases(session_id)
            if not cases:
                raise CouncilConflictError(
                    "At least one case is required before opening."
                )
            attendance_count = await self._council.count_attendees(session_id)
            if attendance_count < council_session.quorum_required:
                raise CouncilConflictError("Confirmed attendance does not meet quorum.")
            for council_case in cases:
                dossier = await self._dossiers.get_by_id(
                    council_case.dossier_id,
                    for_update=True,
                )
                if dossier is None:
                    raise CouncilNotFoundError("Dossier was not found.")
                self._workflow.transition(
                    dossier,
                    target=DossierStatus.COUNCIL_REVIEW,
                    actor_user_id=principal.user_id,
                    allowed_sources={DossierStatus.UNDER_REVIEW},
                    reason_code="COUNCIL_SESSION_OPENED",
                )
            council_session.status = CouncilSessionStatus.OPEN
            council_session.opened_at = self._clock()
            await self._session.flush()
            result = self._session_view(
                council_session,
                member_count=await self._council.count_members(session_id),
                attendance_count=attendance_count,
            )
            self._audit(
                "council.session.opened",
                principal.user_id,
                "council_session",
                session_id,
            )
        return result

    async def declare_conflict(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        *,
        has_conflict: bool,
        reason: str | None,
    ) -> CouncilConflictView:
        self._require_member(principal)
        normalized_reason = self._conflict_reason(has_conflict, reason)
        try:
            async with self._session.begin():
                council_case, _, _ = await self._voting_scope(
                    principal,
                    case_id,
                )
                if await self._council.get_conflict(
                    council_case.id,
                    principal.user_id,
                ):
                    raise CouncilConflictError("Conflict declaration is immutable.")
                declaration = CouncilCaseConflict(
                    id=self._uuid_factory(),
                    case_id=council_case.id,
                    member_user_id=principal.user_id,
                    has_conflict=has_conflict,
                    reason=normalized_reason,
                    declared_at=self._clock(),
                )
                self._council.add_conflict(declaration)
                await self._session.flush()
                result = self._conflict_view(declaration)
                self._audit(
                    "council.conflict.declared",
                    principal.user_id,
                    "council_case",
                    council_case.id,
                )
        except IntegrityError as exc:
            raise CouncilConflictError("Conflict declaration is immutable.") from exc
        return result

    async def cast_vote(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        *,
        choice: CouncilVoteChoice,
        reason: str,
    ) -> CouncilVoteView:
        self._require_member(principal)
        normalized_reason = reason.strip()
        if not normalized_reason or len(normalized_reason) > 2_000:
            raise CouncilValidationError(
                "Vote reason must contain between 1 and 2000 characters."
            )
        try:
            async with self._session.begin():
                council_case, _, _ = await self._voting_scope(
                    principal,
                    case_id,
                )
                declaration = await self._council.get_conflict(
                    council_case.id,
                    principal.user_id,
                )
                if declaration is None:
                    raise CouncilConflictError(
                        "Conflict declaration is required before voting."
                    )
                if declaration.has_conflict:
                    raise CouncilConflictError(
                        "A conflicted member cannot vote on this case."
                    )
                if await self._council.get_vote(
                    council_case.id,
                    principal.user_id,
                ):
                    raise CouncilConflictError("A member may vote only once.")
                vote = CouncilVote(
                    id=self._uuid_factory(),
                    case_id=council_case.id,
                    member_user_id=principal.user_id,
                    choice=choice,
                    reason=normalized_reason,
                    voted_at=self._clock(),
                )
                self._council.add_vote(vote)
                await self._session.flush()
                result = self._vote_view(vote)
                self._audit(
                    "council.vote.cast",
                    principal.user_id,
                    "council_case",
                    council_case.id,
                )
        except IntegrityError as exc:
            raise CouncilConflictError("A member may vote only once.") from exc
        return result

    async def close_session(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilSessionView:
        self._require_secretary(principal)
        async with self._session.begin():
            council_session = await self._required_session(
                session_id,
                for_update=True,
            )
            if council_session.status is not CouncilSessionStatus.OPEN:
                raise CouncilConflictError("Only an open session can be closed.")
            cases = await self._council.list_cases(session_id)
            votes = await self._council.list_votes(tuple(item.id for item in cases))
            votes_by_case = group_votes(votes)
            for council_case in cases:
                result = calculate_case_result(
                    council_case,
                    votes_by_case.get(council_case.id, ()),
                    quorum_required=council_session.quorum_required,
                )
                council_case.decision = result.decision
                if result.decision is not None:
                    dossier = await self._dossiers.get_by_id(
                        council_case.dossier_id,
                        for_update=True,
                    )
                    if dossier is None:
                        raise CouncilNotFoundError("Dossier was not found.")
                    if result.decision is CouncilCaseDecision.APPROVE:
                        version = await self._session.get(
                            DossierVersion,
                            council_case.dossier_version_id,
                        )
                        evidence_rows = await self._dossiers.list_evidences(
                            council_case.dossier_id,
                            version_id=council_case.dossier_version_id,
                        )
                        if version is None or not version_has_trusted_provenance(
                            version,
                            evidence_rows,
                        ):
                            raise CouncilConflictError(
                                "Evidence integrity must be reverified before approval."
                            )
                    self._workflow.transition(
                        dossier,
                        target=DECISION_TARGETS[result.decision],
                        actor_user_id=principal.user_id,
                        allowed_sources={DossierStatus.COUNCIL_REVIEW},
                        reason_code=f"COUNCIL_{result.decision.value}",
                    )
                    if result.decision is CouncilCaseDecision.APPROVE:
                        dossier.approved_at = self._clock()
                    self._add_decision_event(council_case, result.decision)
            council_session.status = CouncilSessionStatus.CLOSED
            council_session.closed_at = self._clock()
            minutes_payload, _ = await self._minutes_payload(
                council_session,
                cases=cases,
                votes=votes,
            )
            council_session.minutes_hash = snapshot_sha256(minutes_payload)
            await self._session.flush()
            result_view = self._session_view(
                council_session,
                member_count=await self._council.count_members(session_id),
                attendance_count=await self._council.count_attendees(session_id),
            )
            self._audit(
                "council.session.closed",
                principal.user_id,
                "council_session",
                session_id,
            )
        return result_view

    async def get_minutes(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilMinutesView:
        async with self._session.begin():
            council_session = await self._required_session(
                session_id,
                for_update=False,
            )
            await self._require_session_access(principal, council_session)
            if (
                council_session.status is not CouncilSessionStatus.CLOSED
                or council_session.closed_at is None
                or council_session.minutes_hash is None
            ):
                raise CouncilConflictError(
                    "Minutes are available only after session closure."
                )
            cases = await self._council.list_cases(session_id)
            votes = await self._council.list_votes(tuple(item.id for item in cases))
            payload, results = await self._minutes_payload(
                council_session,
                cases=cases,
                votes=votes,
            )
            if snapshot_sha256(payload) != council_session.minutes_hash:
                raise CouncilConflictError(
                    "Council minutes integrity verification failed."
                )
            result = CouncilMinutesView(
                session_id=council_session.id,
                session_code=council_session.code,
                closed_at=council_session.closed_at,
                quorum_required=council_session.quorum_required,
                minutes_hash=council_session.minutes_hash,
                cases=results,
            )
        return result

    async def list_sessions(
        self,
        principal: AuthPrincipal,
        *,
        status: CouncilSessionStatus | None,
        page: int,
        page_size: int,
    ) -> CouncilSessionPage:
        if page < 1 or page_size < 1 or page_size > 100:
            raise CouncilValidationError("Council pagination is invalid.")
        member_user_id = self._read_member_filter(principal)
        async with self._session.begin():
            rows, total = await self._council.list_sessions(
                member_user_id=member_user_id,
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            items = tuple(
                CouncilSessionListItemView(
                    session=self._session_view(
                        council_session,
                        member_count=member_count,
                        attendance_count=attendance_count,
                    ),
                    my_attendance_confirmed_at=attendance,
                )
                for (
                    council_session,
                    member_count,
                    attendance_count,
                    attendance,
                ) in rows
            )
        return CouncilSessionPage(items=items, total=total)

    async def get_session(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilSessionDetailView:
        async with self._session.begin():
            council_session = await self._required_session(
                session_id,
                for_update=False,
            )
            await self._require_session_access(principal, council_session)
            membership = await self._council.get_membership(
                session_id,
                principal.user_id,
            )
            case_rows = await self._council.list_case_rows(session_id)
            case_ids = tuple(row[0].id for row in case_rows)
            conflicts = await self._council.list_conflicts(case_ids)
            votes = await self._council.list_votes(case_ids)
            my_conflicts = {
                item.case_id: item
                for item in conflicts
                if item.member_user_id == principal.user_id
            }
            my_votes = {
                item.case_id: item
                for item in votes
                if item.member_user_id == principal.user_id
            }
            votes_by_case = group_votes(votes)
            disclose_result = council_session.status is CouncilSessionStatus.CLOSED
            cases = tuple(
                CouncilCaseDetailView(
                    case=CouncilCaseView(
                        id=council_case.id,
                        session_id=council_case.session_id,
                        dossier_id=dossier.id,
                        dossier_version_id=version.id,
                        dossier_code=dossier.code,
                        dossier_title=dossier.title,
                        version_no=version.version_no,
                        decision=(council_case.decision if disclose_result else None),
                    ),
                    my_conflict=(
                        self._conflict_view(my_conflicts[council_case.id])
                        if council_case.id in my_conflicts
                        else None
                    ),
                    my_vote=(
                        self._vote_view(my_votes[council_case.id])
                        if council_case.id in my_votes
                        else None
                    ),
                    result=(
                        calculate_case_result(
                            council_case,
                            votes_by_case.get(council_case.id, ()),
                            quorum_required=council_session.quorum_required,
                        )
                        if disclose_result
                        else None
                    ),
                )
                for council_case, dossier, version in case_rows
            )
            result = CouncilSessionDetailView(
                session=self._session_view(
                    council_session,
                    member_count=await self._council.count_members(session_id),
                    attendance_count=await self._council.count_attendees(session_id),
                ),
                my_attendance_confirmed_at=(
                    membership.attendance_confirmed_at
                    if membership is not None
                    else None
                ),
                cases=cases,
            )
        return result

    async def _voting_scope(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
    ) -> tuple[CouncilCase, CouncilSession, CouncilSessionMember]:
        council_case = await self._council.get_case(case_id, for_update=True)
        if council_case is None:
            raise CouncilNotFoundError("Council case was not found.")
        council_session = await self._required_session(
            council_case.session_id,
            for_update=True,
        )
        if council_session.status is not CouncilSessionStatus.OPEN:
            raise CouncilConflictError(
                "Council voting is available only in an open session."
            )
        membership = await self._council.get_membership(
            council_session.id,
            principal.user_id,
            for_update=True,
        )
        if membership is None:
            raise CouncilNotFoundError()
        if membership.attendance_confirmed_at is None:
            raise CouncilConflictError(
                "Attendance confirmation is required before voting."
            )
        return council_case, council_session, membership

    async def _require_session_access(
        self,
        principal: AuthPrincipal,
        council_session: CouncilSession,
    ) -> None:
        if AuthorizationPolicy.allows_capability(
            principal,
            PolicyRequirement(
                permission="council.manage", compatible_roles=SECRETARY_ROLES
            ),
        ):
            return
        self._require_member(principal)
        membership = await self._council.get_membership(
            council_session.id,
            principal.user_id,
        )
        if membership is None:
            raise CouncilNotFoundError()

    async def _minutes_payload(
        self,
        council_session: CouncilSession,
        *,
        cases: tuple[CouncilCase, ...],
        votes: tuple[CouncilVote, ...],
    ) -> tuple[dict[str, object], tuple[CouncilCaseResultView, ...]]:
        members = await self._council.list_members(council_session.id)
        conflicts = await self._council.list_conflicts(tuple(item.id for item in cases))
        votes_by_case = group_votes(votes)
        results = tuple(
            calculate_case_result(
                council_case,
                votes_by_case.get(council_case.id, ()),
                quorum_required=council_session.quorum_required,
            )
            for council_case in cases
        )
        payload = build_minutes_payload(
            council_session,
            members=members,
            conflicts=conflicts,
            votes=votes,
            results=results,
        )
        return payload, results

    def _add_decision_event(
        self,
        council_case: CouncilCase,
        decision: CouncilCaseDecision,
    ) -> None:
        encrypted = self._payload_cipher.encrypt(
            {
                "case_id": str(council_case.id),
                "session_id": str(council_case.session_id),
                "dossier_id": str(council_case.dossier_id),
                "decision": decision.value,
            },
            event_type=DECIDED_EVENT,
            aggregate_id=council_case.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=DECIDED_EVENT,
                aggregate_type="council_case",
                aggregate_id=council_case.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=self._clock(),
            )
        )

    async def _required_session(
        self,
        session_id: UUID,
        *,
        for_update: bool,
    ) -> CouncilSession:
        council_session = await self._council.get_session(
            session_id,
            for_update=for_update,
        )
        if council_session is None:
            raise CouncilNotFoundError("Council session was not found.")
        return council_session

    @staticmethod
    def _member_ids(values: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if not values or len(values) > 50 or len(set(values)) != len(values):
            raise CouncilValidationError(
                "Member list must contain between 1 and 50 unique users."
            )
        return values

    @staticmethod
    def _conflict_reason(
        has_conflict: bool,
        reason: str | None,
    ) -> str | None:
        normalized = reason.strip() if reason is not None else ""
        if has_conflict and (not normalized or len(normalized) > 2_000):
            raise CouncilValidationError(
                "Conflict reason must contain between 1 and 2000 characters."
            )
        if not has_conflict and normalized:
            raise CouncilValidationError(
                "Conflict reason must be empty when no conflict exists."
            )
        return normalized or None

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )

    @staticmethod
    def _require_draft(council_session: CouncilSession) -> None:
        if council_session.status is not CouncilSessionStatus.DRAFT:
            raise CouncilConflictError("Only a draft session can be changed.")

    @staticmethod
    def _require_secretary(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="council.manage", compatible_roles=SECRETARY_ROLES
            ),
            CouncilForbiddenError,
        )

    @staticmethod
    def _require_member(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="council.vote",
                compatible_roles=MEMBER_ROLES,
                allow_super_admin=False,
            ),
            CouncilForbiddenError,
        )

    @staticmethod
    def _read_member_filter(principal: AuthPrincipal) -> UUID | None:
        if AuthorizationPolicy.allows_capability(
            principal,
            PolicyRequirement(
                permission="council.manage", compatible_roles=SECRETARY_ROLES
            ),
        ):
            return None
        if AuthorizationPolicy.allows_capability(
            principal,
            PolicyRequirement(
                permission="council.vote",
                compatible_roles=MEMBER_ROLES,
                allow_super_admin=False,
            ),
        ):
            return principal.user_id
        raise CouncilForbiddenError()

    @staticmethod
    def _member_view(member: CouncilSessionMember) -> CouncilMemberView:
        return CouncilMemberView(
            id=member.id,
            session_id=member.session_id,
            member_user_id=member.member_user_id,
            attendance_confirmed_at=member.attendance_confirmed_at,
        )

    @staticmethod
    def _conflict_view(
        conflict: CouncilCaseConflict,
    ) -> CouncilConflictView:
        return CouncilConflictView(
            id=conflict.id,
            case_id=conflict.case_id,
            member_user_id=conflict.member_user_id,
            has_conflict=conflict.has_conflict,
            reason=conflict.reason,
            declared_at=conflict.declared_at,
        )

    @staticmethod
    def _vote_view(vote: CouncilVote) -> CouncilVoteView:
        return CouncilVoteView(
            id=vote.id,
            case_id=vote.case_id,
            member_user_id=vote.member_user_id,
            choice=vote.choice,
            reason=vote.reason,
            voted_at=vote.voted_at,
        )

    @staticmethod
    def _session_view(
        council_session: CouncilSession,
        *,
        member_count: int,
        attendance_count: int,
    ) -> CouncilSessionView:
        return CouncilSessionView(
            id=council_session.id,
            code=council_session.code,
            title=council_session.title,
            scheduled_at=council_session.scheduled_at,
            status=council_session.status,
            quorum_required=council_session.quorum_required,
            opened_at=council_session.opened_at,
            closed_at=council_session.closed_at,
            minutes_hash=council_session.minutes_hash,
            member_count=member_count,
            attendance_count=attendance_count,
        )

    def _audit(
        self,
        action: str,
        user_id: UUID,
        resource_type: str,
        aggregate_id: UUID,
    ) -> None:
        self._audit_service.record(
            actor_user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(aggregate_id),
        )

    async def close(self) -> None:
        await self._session.close()
