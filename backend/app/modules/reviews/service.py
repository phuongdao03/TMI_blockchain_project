from collections.abc import Callable, Mapping
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
from app.modules.dossiers.models import DossierStatus
from app.modules.dossiers.repository import DossierRepository
from app.modules.reviews.errors import (
    ReviewConflictError,
    ReviewForbiddenError,
    ReviewNotFoundError,
    ReviewValidationError,
)
from app.modules.reviews.models import (
    Review,
    ReviewAssignment,
    ReviewAssignmentStatus,
    ReviewFindingAction,
    ReviewFindingSeverity,
    ReviewRecommendation,
)
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.types import (
    ReviewAssignmentDetailView,
    ReviewAssignmentPage,
    ReviewAssignmentSummaryView,
    ReviewAssignmentView,
    ReviewDraft,
    ReviewFinding,
    ReviewView,
)

ASSIGNMENT_CREATED_EVENT = "review.assignment_created"
REVIEW_COMPLETED_EVENT = "review.completed"
ADMIN_ROLES = frozenset({"SUPER_ADMIN"})
REVIEWER_ROLES = frozenset({"MODERATOR"})
CRITERIA = (
    "truth",
    "transparency",
    "ownership",
    "professionalism",
    "respect",
)
REVIEW_CHECKLIST_KEYS = frozenset(
    {
        "evidence_reviewed",
        "criteria_assessed",
        "findings_recorded",
        "similarity_checked",
        "attestation",
    }
)


class ReviewService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        payload_cipher: OutboxPayloadCipher,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._session = session
        self._reviews = ReviewRepository(session)
        self._dossiers = DossierRepository(session)
        self._outbox = OutboxRepository(session)
        self._audit_service = AuditService(session)
        self._payload_cipher = payload_cipher
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    async def assign_reviewers(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        reviewer_user_ids: tuple[UUID, ...],
        due_at: datetime | None,
    ) -> tuple[ReviewAssignmentView, ...]:
        self._require_admin(principal)
        reviewer_ids = self._reviewer_ids(reviewer_user_ids)
        normalized_due_at = self._due_at(due_at)
        try:
            async with self._session.begin():
                dossier = await self._dossiers.get_by_id(
                    dossier_id,
                    for_update=True,
                )
                if dossier is None:
                    raise ReviewNotFoundError("Dossier was not found.")
                if (
                    dossier.status is not DossierStatus.UNDER_REVIEW
                    or dossier.current_version_no <= 0
                ):
                    raise ReviewConflictError(
                        "Reviewers can be assigned only to the current "
                        "UNDER_REVIEW dossier version."
                    )
                version = await self._dossiers.get_version(
                    dossier.id,
                    dossier.current_version_no,
                )
                if version is None:
                    raise ReviewConflictError(
                        "The current dossier version could not be found."
                    )

                assignments: list[ReviewAssignment] = []
                for reviewer_id in reviewer_ids:
                    reviewer = await self._reviews.get_active_reviewer(reviewer_id)
                    if reviewer is None:
                        raise ReviewValidationError(
                            "Every assignee must be an active reviewer."
                        )
                    if reviewer.id == dossier.owner_user_id:
                        raise ReviewValidationError(
                            "A dossier owner cannot review their own dossier."
                        )
                    if await self._reviews.get_active_assignment(
                        reviewer.id,
                        version.id,
                    ):
                        raise ReviewConflictError(
                            "Reviewer already has an active assignment "
                            "for this version."
                        )
                    assignment = ReviewAssignment(
                        id=self._uuid_factory(),
                        dossier_id=dossier.id,
                        dossier_version_id=version.id,
                        reviewer_user_id=reviewer.id,
                        assigned_by=principal.user_id,
                        due_at=normalized_due_at,
                        status=ReviewAssignmentStatus.ASSIGNED,
                    )
                    self._reviews.add_assignment(assignment)
                    self._add_assignment_event(assignment)
                    assignments.append(assignment)
                await self._session.flush()
                result = tuple(self._assignment_view(item) for item in assignments)
                self._audit_assignment(
                    principal.user_id,
                    dossier_id,
                    assignment_count=len(result),
                )
        except IntegrityError as exc:
            raise ReviewConflictError(
                "Reviewer already has an active assignment for this version."
            ) from exc
        return result

    async def list_assignments(
        self,
        principal: AuthPrincipal,
        *,
        status: ReviewAssignmentStatus | None,
        page: int,
        page_size: int,
    ) -> ReviewAssignmentPage:
        self._require_reviewer(principal)
        if page < 1 or page_size < 1 or page_size > 100:
            raise ReviewValidationError("Review pagination is invalid.")
        async with self._session.begin():
            rows, total = await self._reviews.list_owned_assignments(
                principal.user_id,
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            items = tuple(
                ReviewAssignmentSummaryView(
                    assignment=self._assignment_view(assignment),
                    dossier_code=dossier.code,
                    dossier_title=self._snapshot_title(
                        version.snapshot_json,
                        fallback=dossier.title,
                    ),
                    version_no=version.version_no,
                )
                for assignment, dossier, version in rows
            )
        return ReviewAssignmentPage(items=items, total=total)

    async def get_assignment(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
    ) -> ReviewAssignmentDetailView:
        self._require_reviewer(principal)
        async with self._session.begin():
            assignment = await self._owned_assignment(
                principal,
                assignment_id,
            )
            dossier = await self._dossiers.get_by_id(assignment.dossier_id)
            version = await self._reviews.get_version(assignment.dossier_version_id)
            if dossier is None or version is None:
                raise ReviewNotFoundError()
            review = await self._reviews.get_review(assignment.id)
            can_view_sensitive = assignment.status in (
                ReviewAssignmentStatus.IN_PROGRESS,
                ReviewAssignmentStatus.SUBMITTED,
            )
            return ReviewAssignmentDetailView(
                assignment=self._assignment_view(assignment),
                dossier_code=dossier.code,
                dossier_title=self._snapshot_title(
                    version.snapshot_json,
                    fallback=dossier.title,
                ),
                version_no=version.version_no,
                canonical_hash=(version.canonical_hash if can_view_sensitive else None),
                snapshot_json=(version.snapshot_json if can_view_sensitive else None),
                review=self._review_view(review) if review is not None else None,
            )

    async def declare_conflict(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
        *,
        has_conflict: bool,
        reason: str | None,
    ) -> ReviewAssignmentView:
        self._require_reviewer(principal)
        normalized_reason = self._conflict_reason(has_conflict, reason)
        async with self._session.begin():
            assignment = await self._owned_assignment(
                principal,
                assignment_id,
                for_update=True,
            )
            if assignment.status is not ReviewAssignmentStatus.ASSIGNED:
                raise ReviewConflictError(
                    "Conflict declaration has already been completed."
                )
            assignment.conflict_declared_at = self._clock()
            assignment.conflict_reason = normalized_reason
            assignment.status = (
                ReviewAssignmentStatus.CONFLICTED
                if has_conflict
                else ReviewAssignmentStatus.IN_PROGRESS
            )
            await self._session.flush()
            result = self._assignment_view(assignment)
            self._audit_review(
                "review.conflict_declared",
                principal.user_id,
                assignment_id,
            )
        return result

    async def save_draft(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
        draft: ReviewDraft,
    ) -> ReviewView:
        self._require_reviewer(principal)
        validated = self._validated_draft(draft)
        async with self._session.begin():
            assignment = await self._owned_assignment(
                principal,
                assignment_id,
                for_update=True,
            )
            if assignment.status is not ReviewAssignmentStatus.IN_PROGRESS:
                raise ReviewConflictError(
                    "Only an in-progress assignment accepts draft changes."
                )
            version = await self._reviews.get_version(assignment.dossier_version_id)
            if version is None:
                raise ReviewNotFoundError()
            self._validate_evidence_references(validated, version.snapshot_json)
            review = await self._reviews.get_review(
                assignment.id,
                for_update=True,
            )
            if review is None:
                review = Review(
                    id=self._uuid_factory(),
                    assignment_id=assignment.id,
                )
                self._reviews.add_review(review)
            self._apply_draft(review, validated)
            await self._session.flush()
            result = self._review_view(review)
            self._audit_review(
                "review.draft_saved",
                principal.user_id,
                assignment_id,
            )
        return result

    async def submit_review(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
    ) -> ReviewView:
        self._require_reviewer(principal)
        async with self._session.begin():
            assignment = await self._owned_assignment(
                principal,
                assignment_id,
                for_update=True,
            )
            if assignment.status is not ReviewAssignmentStatus.IN_PROGRESS:
                raise ReviewConflictError(
                    "Only an in-progress assignment can be submitted."
                )
            review = await self._reviews.get_review(
                assignment.id,
                for_update=True,
            )
            if review is None:
                raise ReviewValidationError(
                    "A complete 5T draft is required before submission."
                )
            scores = self._complete_scores(review)
            review.total_score = sum(scores)
            review.submitted_at = self._clock()
            assignment.status = ReviewAssignmentStatus.SUBMITTED
            self._add_review_completed_event(assignment)
            await self._session.flush()
            result = self._review_view(review)
            self._audit_review(
                "review.submitted",
                principal.user_id,
                assignment_id,
            )
        return result

    def _add_assignment_event(self, assignment: ReviewAssignment) -> None:
        encrypted = self._payload_cipher.encrypt(
            {
                "assignment_id": str(assignment.id),
                "dossier_id": str(assignment.dossier_id),
                "recipient_user_id": str(assignment.reviewer_user_id),
            },
            event_type=ASSIGNMENT_CREATED_EVENT,
            aggregate_id=assignment.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=ASSIGNMENT_CREATED_EVENT,
                aggregate_type="review_assignment",
                aggregate_id=assignment.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=self._clock(),
            )
        )

    def _add_review_completed_event(self, assignment: ReviewAssignment) -> None:
        encrypted = self._payload_cipher.encrypt(
            {
                "assignment_id": str(assignment.id),
                "dossier_id": str(assignment.dossier_id),
            },
            event_type=REVIEW_COMPLETED_EVENT,
            aggregate_id=assignment.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=REVIEW_COMPLETED_EVENT,
                aggregate_type="review_assignment",
                aggregate_id=assignment.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=self._clock(),
            )
        )

    async def _owned_assignment(
        self,
        principal: AuthPrincipal,
        assignment_id: UUID,
        *,
        for_update: bool = False,
    ) -> ReviewAssignment:
        assignment = await self._reviews.get_owned_assignment(
            assignment_id,
            principal.user_id,
            for_update=for_update,
        )
        if assignment is None:
            raise ReviewNotFoundError()
        return assignment

    @staticmethod
    def _snapshot_title(
        snapshot: dict[str, object],
        *,
        fallback: str,
    ) -> str:
        dossier = snapshot.get("dossier")
        if isinstance(dossier, dict):
            title = dossier.get("title")
            if isinstance(title, str) and title:
                return title
        return fallback

    @staticmethod
    def _conflict_reason(
        has_conflict: bool,
        reason: str | None,
    ) -> str | None:
        normalized = reason.strip() if reason is not None else ""
        if has_conflict and (not normalized or len(normalized) > 2_000):
            raise ReviewValidationError(
                "Conflict reason must contain between 1 and 2000 characters."
            )
        if not has_conflict and normalized:
            raise ReviewValidationError(
                "Conflict reason must be empty when no conflict exists."
            )
        return normalized or None

    @classmethod
    def _validated_draft(cls, draft: ReviewDraft) -> ReviewDraft:
        scores = (
            draft.truth_score,
            draft.transparency_score,
            draft.ownership_score,
            draft.professionalism_score,
            draft.respect_score,
        )
        for score in scores:
            if score is not None and (
                isinstance(score, bool) or score < 0 or score > 20
            ):
                raise ReviewValidationError(
                    "Every provided 5T score must be between 0 and 20."
                )
        if set(draft.criterion_comments) - set(CRITERIA):
            raise ReviewValidationError("Criterion comment key is invalid.")
        comments: dict[str, str] = {}
        for criterion, comment in draft.criterion_comments.items():
            normalized = comment.strip()
            if len(normalized) > 2_000:
                raise ReviewValidationError(
                    "Criterion comments cannot exceed 2000 characters."
                )
            comments[criterion] = normalized
        if set(draft.criterion_evidence) - set(CRITERIA):
            raise ReviewValidationError("Criterion evidence key is invalid.")
        criterion_evidence: dict[str, tuple[UUID, ...]] = {}
        for criterion, media_ids in draft.criterion_evidence.items():
            values = tuple(media_ids)
            if (
                len(values) > 10
                or len(values) != len(set(values))
                or any(not isinstance(media_id, UUID) for media_id in values)
            ):
                raise ReviewValidationError("Criterion evidence is invalid.")
            criterion_evidence[criterion] = values
        if len(draft.findings) > 20:
            raise ReviewValidationError("A review can contain at most 20 findings.")
        findings = tuple(cls._validated_finding(item) for item in draft.findings)
        if len({item.id for item in findings}) != len(findings):
            raise ReviewValidationError("Finding identifiers must be unique.")
        if set(draft.checklist_answers) - REVIEW_CHECKLIST_KEYS:
            raise ReviewValidationError("Review checklist key is invalid.")
        checklist_answers: dict[str, bool] = {}
        for key, answer in draft.checklist_answers.items():
            if not isinstance(answer, bool):
                raise ReviewValidationError("Review checklist answers must be boolean.")
            checklist_answers[key] = answer
        applicant_feedback = (
            draft.applicant_feedback.strip()
            if draft.applicant_feedback is not None
            else ""
        )
        if len(applicant_feedback) > 2_000:
            raise ReviewValidationError(
                "Applicant feedback cannot exceed 2000 characters."
            )
        private_note = (
            draft.private_note.strip() if draft.private_note is not None else ""
        )
        if len(private_note) > 5_000:
            raise ReviewValidationError("Private note cannot exceed 5000 characters.")
        return ReviewDraft(
            truth_score=draft.truth_score,
            transparency_score=draft.transparency_score,
            ownership_score=draft.ownership_score,
            professionalism_score=draft.professionalism_score,
            respect_score=draft.respect_score,
            criterion_comments=comments,
            criterion_evidence=criterion_evidence,
            findings=findings,
            checklist_answers=checklist_answers,
            applicant_feedback=applicant_feedback or None,
            recommendation=draft.recommendation,
            private_note=private_note or None,
        )

    @staticmethod
    def _validated_finding(finding: ReviewFinding) -> ReviewFinding:
        if (
            not isinstance(finding.id, UUID)
            or finding.criterion not in CRITERIA
            or not isinstance(finding.severity, ReviewFindingSeverity)
            or not isinstance(finding.action, ReviewFindingAction)
        ):
            raise ReviewValidationError("Review finding is invalid.")
        evidence_media_ids = tuple(finding.evidence_media_ids)
        if (
            not evidence_media_ids
            or len(evidence_media_ids) > 10
            or len(evidence_media_ids) != len(set(evidence_media_ids))
            or any(not isinstance(item, UUID) for item in evidence_media_ids)
        ):
            raise ReviewValidationError("Finding evidence is invalid.")
        title = " ".join(finding.title.split())
        description = finding.description.strip()
        if not 5 <= len(title) <= 240 or not 20 <= len(description) <= 2_000:
            raise ReviewValidationError("Review finding content is invalid.")
        if (
            finding.severity
            in {ReviewFindingSeverity.HIGH, ReviewFindingSeverity.CRITICAL}
            and finding.action is not ReviewFindingAction.ESCALATE
        ):
            raise ReviewValidationError("High-risk findings must be escalated.")
        return ReviewFinding(
            id=finding.id,
            severity=finding.severity,
            criterion=finding.criterion,
            evidence_media_ids=evidence_media_ids,
            title=title,
            description=description,
            action=finding.action,
        )

    @staticmethod
    def _validate_evidence_references(
        draft: ReviewDraft,
        snapshot: Mapping[str, object],
    ) -> None:
        raw_evidences = snapshot.get("evidences")
        allowed: set[UUID] = set()
        if isinstance(raw_evidences, list):
            for evidence in raw_evidences:
                if not isinstance(evidence, dict):
                    continue
                raw_media_id = evidence.get("mediaAssetId")
                if not isinstance(raw_media_id, str):
                    continue
                try:
                    allowed.add(UUID(raw_media_id))
                except ValueError:
                    continue
        referenced = {
            media_id
            for values in draft.criterion_evidence.values()
            for media_id in values
        }
        referenced.update(
            media_id
            for finding in draft.findings
            for media_id in finding.evidence_media_ids
        )
        if not referenced.issubset(allowed):
            raise ReviewValidationError(
                "Evidence references must belong to the locked dossier version."
            )

    @staticmethod
    def _apply_draft(review: Review, draft: ReviewDraft) -> None:
        review.truth_score = draft.truth_score
        review.transparency_score = draft.transparency_score
        review.ownership_score = draft.ownership_score
        review.professionalism_score = draft.professionalism_score
        review.respect_score = draft.respect_score
        review.criterion_comments = dict(draft.criterion_comments)
        review.criterion_evidence = {
            criterion: [str(media_id) for media_id in media_ids]
            for criterion, media_ids in draft.criterion_evidence.items()
        }
        review.findings = [
            {
                "id": str(finding.id),
                "severity": finding.severity.value,
                "criterion": finding.criterion,
                "evidenceMediaIds": [
                    str(media_id) for media_id in finding.evidence_media_ids
                ],
                "title": finding.title,
                "description": finding.description,
                "action": finding.action.value,
            }
            for finding in draft.findings
        ]
        review.checklist_answers = dict(draft.checklist_answers)
        review.applicant_feedback = draft.applicant_feedback
        review.recommendation = draft.recommendation
        review.private_note = draft.private_note
        scores = (
            draft.truth_score,
            draft.transparency_score,
            draft.ownership_score,
            draft.professionalism_score,
            draft.respect_score,
        )
        review.total_score = (
            sum(score for score in scores if score is not None)
            if all(score is not None for score in scores)
            else None
        )

    @classmethod
    def _complete_scores(cls, review: Review) -> tuple[int, ...]:
        scores = cls._review_scores(review)
        if len(scores) != len(CRITERIA):
            raise ReviewValidationError("All five 5T scores are required.")
        if review.recommendation is None:
            raise ReviewValidationError("Review recommendation is required.")
        if set(review.criterion_comments) != set(CRITERIA) or any(
            not review.criterion_comments[criterion].strip() for criterion in CRITERIA
        ):
            raise ReviewValidationError(
                "A non-empty comment is required for every 5T criterion."
            )
        criterion_evidence = cls._criterion_evidence_from_review(review)
        if set(criterion_evidence) != set(CRITERIA) or any(
            not criterion_evidence[criterion] for criterion in CRITERIA
        ):
            raise ReviewValidationError(
                "At least one evidence reference is required for every 5T criterion."
            )
        if set(review.checklist_answers) != REVIEW_CHECKLIST_KEYS or not all(
            review.checklist_answers.values()
        ):
            raise ReviewValidationError(
                "All review completion checklist items must be confirmed."
            )
        findings = cls._findings_from_review(review)
        high_risk = {
            ReviewFindingSeverity.HIGH,
            ReviewFindingSeverity.CRITICAL,
        }
        if review.recommendation is ReviewRecommendation.APPROVE:
            if sum(scores) < 70:
                raise ReviewValidationError(
                    "Approval recommendation requires a score of at least 70."
                )
            if any(finding.severity in high_risk for finding in findings):
                raise ReviewValidationError(
                    "High-risk findings must be resolved outside an approval "
                    "recommendation."
                )
        if review.recommendation in {
            ReviewRecommendation.SUPPLEMENT,
            ReviewRecommendation.REJECT,
        } and (
            review.applicant_feedback is None or len(review.applicant_feedback) < 50
        ):
            raise ReviewValidationError(
                "A meaningful applicant-facing explanation is required."
            )
        if review.recommendation is ReviewRecommendation.SUPPLEMENT and not any(
            finding.action is ReviewFindingAction.SUPPLEMENT for finding in findings
        ):
            raise ReviewValidationError(
                "A supplement recommendation requires a supplement finding."
            )
        if review.recommendation is ReviewRecommendation.REJECT and (
            sum(scores) >= 50
            and not any(
                finding.severity is ReviewFindingSeverity.CRITICAL
                for finding in findings
            )
        ):
            raise ReviewValidationError(
                "A rejection requires a score below 50 or a critical finding."
            )
        return scores

    @staticmethod
    def _criterion_evidence_from_review(
        review: Review,
    ) -> dict[str, tuple[UUID, ...]]:
        result: dict[str, tuple[UUID, ...]] = {}
        for criterion, raw_values in review.criterion_evidence.items():
            if not isinstance(raw_values, list):
                raise ReviewValidationError("Stored criterion evidence is invalid.")
            try:
                result[criterion] = tuple(UUID(str(item)) for item in raw_values)
            except ValueError as exc:
                raise ReviewValidationError(
                    "Stored criterion evidence is invalid."
                ) from exc
        return result

    @staticmethod
    def _findings_from_review(review: Review) -> tuple[ReviewFinding, ...]:
        findings: list[ReviewFinding] = []
        for raw in review.findings:
            if not isinstance(raw, dict):
                raise ReviewValidationError("Stored review finding is invalid.")
            raw_media_ids = raw.get("evidenceMediaIds")
            if not isinstance(raw_media_ids, list):
                raise ReviewValidationError("Stored review finding is invalid.")
            try:
                finding = ReviewFinding(
                    id=UUID(str(raw["id"])),
                    severity=ReviewFindingSeverity(str(raw["severity"])),
                    criterion=str(raw["criterion"]),
                    evidence_media_ids=tuple(
                        UUID(str(media_id)) for media_id in raw_media_ids
                    ),
                    title=str(raw["title"]),
                    description=str(raw["description"]),
                    action=ReviewFindingAction(str(raw["action"])),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ReviewValidationError(
                    "Stored review finding is invalid."
                ) from exc
            findings.append(ReviewService._validated_finding(finding))
        return tuple(findings)

    @staticmethod
    def _review_scores(review: Review) -> tuple[int, ...]:
        values = (
            review.truth_score,
            review.transparency_score,
            review.ownership_score,
            review.professionalism_score,
            review.respect_score,
        )
        return tuple(score for score in values if score is not None)

    @staticmethod
    def _review_view(review: Review) -> ReviewView:
        return ReviewView(
            id=review.id,
            assignment_id=review.assignment_id,
            truth_score=review.truth_score,
            transparency_score=review.transparency_score,
            ownership_score=review.ownership_score,
            professionalism_score=review.professionalism_score,
            respect_score=review.respect_score,
            total_score=review.total_score,
            recommendation=review.recommendation,
            criterion_comments=dict(review.criterion_comments),
            criterion_evidence=ReviewService._criterion_evidence_from_review(review),
            findings=ReviewService._findings_from_review(review),
            checklist_answers=dict(review.checklist_answers),
            applicant_feedback=review.applicant_feedback,
            private_note=review.private_note,
            submitted_at=review.submitted_at,
        )

    @staticmethod
    def _reviewer_ids(values: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if not values or len(values) > 50 or len(set(values)) != len(values):
            raise ReviewValidationError(
                "Reviewer list must contain between 1 and 50 unique users."
            )
        return values

    def _due_at(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        normalized = (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )
        if normalized <= self._clock():
            raise ReviewValidationError("Assignment due date must be in the future.")
        return normalized

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(permission="review.assign", compatible_roles=ADMIN_ROLES),
            ReviewForbiddenError,
        )

    @staticmethod
    def _require_reviewer(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="review.submit",
                compatible_roles=REVIEWER_ROLES,
                allow_super_admin=False,
            ),
            ReviewForbiddenError,
        )

    @staticmethod
    def _assignment_view(assignment: ReviewAssignment) -> ReviewAssignmentView:
        return ReviewAssignmentView(
            id=assignment.id,
            dossier_id=assignment.dossier_id,
            dossier_version_id=assignment.dossier_version_id,
            reviewer_user_id=assignment.reviewer_user_id,
            assigned_by=assignment.assigned_by,
            due_at=assignment.due_at,
            status=assignment.status,
            conflict_declared_at=assignment.conflict_declared_at,
            conflict_reason=assignment.conflict_reason,
        )

    def _audit_assignment(
        self,
        user_id: UUID,
        dossier_id: UUID,
        *,
        assignment_count: int,
    ) -> None:
        self._audit_service.record(
            actor_user_id=user_id,
            action="review.assignments.created",
            resource_type="dossier",
            resource_id=str(dossier_id),
            after={"assignment_count": assignment_count},
        )

    def _audit_review(
        self,
        action: str,
        user_id: UUID,
        assignment_id: UUID,
    ) -> None:
        self._audit_service.record(
            actor_user_id=user_id,
            action=action,
            resource_type="review_assignment",
            resource_id=str(assignment_id),
        )

    async def close(self) -> None:
        await self._session.close()
