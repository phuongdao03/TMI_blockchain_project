from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVersion
from app.modules.dossiers.repository import DossierRepository
from app.modules.reviews.models import ReviewAssignment, ReviewAssignmentStatus
from app.modules.supplements.models import SupplementRequest, SupplementResponse
from app.modules.supplements.repository import SupplementRepository
from app.modules.supplements.schemas import SupplementData


def error(status: int, message: str) -> DomainError:
    return DomainError(code=f"SUPPLEMENT_{status}", message=message, status_code=status)


async def require_answered(session: AsyncSession, dossier_id: UUID) -> None:
    if await SupplementRepository(session).count(dossier_id, states=("OPEN",)):
        raise error(409, "Respond to all open supplement requests before resubmitting.")


async def require_resolved(session: AsyncSession, dossier_id: UUID) -> None:
    if await SupplementRepository(session).count(
        dossier_id, states=("OPEN", "ANSWERED")
    ):
        raise error(409, "Resolve all supplement requests before approval.")


class SupplementService:
    def __init__(
        self, session: AsyncSession, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(UTC))
        self._repo = SupplementRepository(session)
        self._dossiers = DossierRepository(session)
        self._audit = AuditService(session)

    async def _scope(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        staff: bool,
        lock: bool = False,
    ) -> Dossier:
        dossier = await self._dossiers.get_by_id(dossier_id, for_update=lock)
        if dossier is None:
            raise error(404, "Dossier not found.")
        admin = AuthorizationPolicy.allows_capability(
            principal,
            PolicyRequirement(
                permission="review.assign", compatible_roles=frozenset({"SUPER_ADMIN"})
            ),
        )
        if not staff and principal.user_id == dossier.owner_user_id:
            return dossier
        if staff and principal.user_id == dossier.owner_user_id:
            raise error(404, "Supplement request not found.")
        if admin:
            return dossier
        if not AuthorizationPolicy.allows_capability(
            principal,
            PolicyRequirement(
                permission="review.submit", compatible_roles=frozenset({"MODERATOR"})
            ),
        ):
            raise error(404, "Supplement request not found.")
        assignment = await self._session.scalar(
            select(ReviewAssignment.id)
            .join(
                DossierVersion, DossierVersion.id == ReviewAssignment.dossier_version_id
            )
            .where(
                ReviewAssignment.dossier_id == dossier.id,
                DossierVersion.version_no == dossier.current_version_no,
                ReviewAssignment.reviewer_user_id == principal.user_id,
                ReviewAssignment.status.in_(
                    (
                        ReviewAssignmentStatus.IN_PROGRESS,
                        ReviewAssignmentStatus.SUBMITTED,
                    )
                ),
                ReviewAssignment.conflict_declared_at.is_not(None),
                ReviewAssignment.conflict_reason.is_(None),
            )
        )
        if assignment is None or principal.user_id == dossier.owner_user_id:
            raise error(404, "Supplement request not found.")
        return dossier

    async def list(
        self, principal: AuthPrincipal, dossier_id: UUID
    ) -> tuple[SupplementData, ...]:
        async with self._session.begin():
            dossier = await self._scope(principal, dossier_id, staff=False)
            owner = principal.user_id == dossier.owner_user_id
            rows = await self._repo.list(
                dossier_id,
                include_open=not owner
                or dossier.status is DossierStatus.NEEDS_SUPPLEMENT,
            )
            return tuple(SupplementData.model_validate(row) for row in rows)

    @staticmethod
    def _text(value: str) -> str:
        if not isinstance(value, str) or not 20 <= len(value.strip()) <= 2000:
            raise error(422, "Provide a concrete explanation of 20 to 2000 characters.")
        return value.strip()

    async def create(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        criterion_key: str,
        expected_version_id: UUID,
        requested_information: str,
        reason: str,
        priority: str = "NORMAL",
        due_at: datetime | None = None,
        claim_id: UUID | None = None,
    ) -> SupplementData:
        async with self._session.begin():
            dossier = await self._scope(principal, dossier_id, staff=True, lock=True)
            if dossier.status not in {
                DossierStatus.PRECHECK,
                DossierStatus.UNDER_REVIEW,
                DossierStatus.NEEDS_SUPPLEMENT,
            }:
                raise error(409, "Supplement requests require an active review.")
            version = await self._dossiers.get_version(
                dossier.id, dossier.current_version_no
            )
            if version is None:
                raise error(409, "A submitted dossier version is required.")
            if version.id != expected_version_id:
                raise error(
                    409,
                    "The dossier version changed. Reload before requesting changes.",
                )
            content = version.snapshot_json.get("dossier", {})
            dossier_type = (
                content.get("dossierType", {}) if isinstance(content, Mapping) else {}
            )
            rubric = (
                dossier_type.get("reviewRubric", {})
                if isinstance(dossier_type, Mapping)
                else {}
            )
            criteria = rubric.get("criteria", []) if isinstance(rubric, Mapping) else []
            criterion = next(
                (
                    item
                    for item in criteria
                    if isinstance(item, Mapping) and item.get("key") == criterion_key
                ),
                None,
            )
            if criterion is None:
                raise error(
                    422, "The criterion must belong to the submitted dossier version."
                )
            claims = content.get("claims", []) if isinstance(content, Mapping) else []
            if claim_id is not None and not any(
                isinstance(claim, Mapping)
                and claim.get("id") == str(claim_id)
                and claim.get("criterionKey") == criterion_key
                for claim in claims
            ):
                raise error(422, "The claim must belong to this frozen criterion.")
            if priority not in {"NORMAL", "HIGH"}:
                raise error(422, "Invalid supplement priority.")
            if due_at is not None and (
                due_at.tzinfo is None or due_at <= self._clock()
            ):
                raise error(
                    422,
                    "An explicit deadline must be timezone-aware and in the future.",
                )
            if (
                await self._repo.count(
                    dossier_id, states=("OPEN", "ANSWERED", "RESOLVED")
                )
                >= 100
            ):
                raise error(409, "This dossier already has 100 supplement requests.")
            row = SupplementRequest(
                dossier_id=dossier.id,
                requested_version_id=version.id,
                criterion_key=criterion_key,
                criterion_label=str(criterion.get("label", criterion_key)),
                claim_id=claim_id,
                requested_information=self._text(requested_information),
                reason=self._text(reason),
                priority=priority,
                due_at=due_at,
                created_by=principal.user_id,
                created_at=self._clock(),
                status="OPEN",
                revision=0,
            )
            self._session.add(row)
            await self._session.flush()
            await self._session.refresh(row, ["responses"])
            self._record(principal, row, "created")
            return SupplementData.model_validate(row)

    async def respond(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        request_id: UUID,
        *,
        expected_revision: int,
        text: str,
    ) -> SupplementData:
        async with self._session.begin():
            dossier = await self._scope(principal, dossier_id, staff=False, lock=True)
            if principal.user_id != dossier.owner_user_id:
                raise error(404, "Supplement request not found.")
            if dossier.status is not DossierStatus.NEEDS_SUPPLEMENT:
                raise error(
                    409, "Responses require a dossier open for supplementation."
                )
            row = await self._required(dossier_id, request_id, expected_revision)
            if row.status != "OPEN":
                raise error(409, "Only an open request accepts a response.")
            self._append(principal, row, "RESPONSE", text)
            row.status = "ANSWERED"
            await self._session.flush()
            await self._session.refresh(row, ["responses"])
            self._record(principal, row, "answered")
            return SupplementData.model_validate(row)

    async def decide(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        request_id: UUID,
        *,
        expected_revision: int,
        resolution: str,
        reopen: bool,
    ) -> SupplementData:
        async with self._session.begin():
            dossier = await self._scope(principal, dossier_id, staff=True, lock=True)
            if dossier.status not in {
                DossierStatus.PRECHECK,
                DossierStatus.UNDER_REVIEW,
                DossierStatus.NEEDS_SUPPLEMENT,
                DossierStatus.COUNCIL_REVIEW,
            }:
                raise error(409, "Supplement handling requires an active review.")
            row = await self._required(dossier_id, request_id, expected_revision)
            if (reopen and row.status == "OPEN") or (
                not reopen and row.status == "RESOLVED"
            ):
                raise error(409, "The request is already in that state.")
            self._append(principal, row, "REOPEN" if reopen else "RESOLVE", resolution)
            row.status = "OPEN" if reopen else "RESOLVED"
            await self._session.flush()
            await self._session.refresh(row, ["responses"])
            self._record(principal, row, "reopened" if reopen else "resolved")
            return SupplementData.model_validate(row)

    async def _required(
        self, dossier_id: UUID, request_id: UUID, revision: int
    ) -> SupplementRequest:
        row = await self._repo.get(dossier_id, request_id)
        if row is None:
            raise error(404, "Supplement request not found.")
        if isinstance(revision, bool) or revision != row.revision:
            raise error(409, "This request changed. Reload before continuing.")
        return row

    def _append(
        self, principal: AuthPrincipal, row: SupplementRequest, kind: str, content: str
    ) -> None:
        self._session.add(
            SupplementResponse(
                request_id=row.id,
                author_id=principal.user_id,
                kind=kind,
                sequence_no=row.revision + 1,
                text=self._text(content),
                created_at=self._clock(),
            )
        )
        row.revision += 1

    def _record(
        self, principal: AuthPrincipal, row: SupplementRequest, action: str
    ) -> None:
        self._audit.record(
            actor_user_id=principal.user_id,
            action=f"supplement.{action}",
            resource_type="supplement_request",
            resource_id=str(row.id),
            after={
                "dossier_id": str(row.dossier_id),
                "revision": row.revision,
                "status": row.status,
            },
        )

    async def close(self) -> None:
        await self._session.close()
