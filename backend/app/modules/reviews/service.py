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
        "attestation",
    }
)
# Kept as an accepted draft key so reviews saved before the similarity module was
# retired remain readable. It is no longer required to submit a review.
REVIEW_CHECKLIST_LEGACY_KEYS = frozenset({"similarity_checked"})


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
                        status=ReviewAssignmentStatus.IN_PROGRESS,
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
            self._validate_specialist_answers(validated, version.snapshot_json)
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
            rubric = self._rubric_from_snapshot(version.snapshot_json)
            review.rubric_version = (
                str(rubric["version"]) if rubric is not None else None
            )
            review.specialist_score = self._specialist_score(
                review, rubric, require_complete=False
            )
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
            version = await self._reviews.get_version(assignment.dossier_version_id)
            if version is None:
                raise ReviewNotFoundError()
            self._validate_complete_evidence_assessments(review, version.snapshot_json)
            rubric = self._rubric_from_snapshot(version.snapshot_json)
            if rubric is not None and self._is_verdict_rubric(rubric):
                self._validate_verdict_decision(review, rubric)
                review.specialist_score = None
                review.total_score = None
            else:
                scores = self._complete_scores(review)
                review.specialist_score = self._specialist_score(
                    review, rubric, require_complete=True
                )
                self._validate_specialist_decision(review, rubric)
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
        if set(draft.checklist_answers) - (
            REVIEW_CHECKLIST_KEYS | REVIEW_CHECKLIST_LEGACY_KEYS
        ):
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
            gate_answers=cls._validated_answer_map(
                draft.gate_answers, require_score=False, evidence_required=False
            ),
            specialist_answers=cls._validated_answer_map(
                draft.specialist_answers, require_score=True, evidence_required=True
            ),
            criterion_verdicts=cls._validated_verdict_map(draft.criterion_verdicts),
            evidence_assessments=cls._validated_evidence_assessments(
                draft.evidence_assessments
            ),
        )

    @staticmethod
    def _validated_evidence_assessments(
        assessments: Mapping[str, Mapping[str, object]],
    ) -> dict[str, dict[str, object]]:
        if len(assessments) > 100:
            raise ReviewValidationError(
                "A review can assess at most 100 evidence files."
            )
        allowed_statuses = {
            "UNREVIEWED",
            "VALID",
            "NEEDS_CLARIFICATION",
            "NOT_RELEVANT",
        }
        result: dict[str, dict[str, object]] = {}
        for raw_media_id, assessment in assessments.items():
            try:
                media_id = str(UUID(raw_media_id))
            except (TypeError, ValueError) as exc:
                raise ReviewValidationError(
                    "Evidence assessment identifier is invalid."
                ) from exc
            if not isinstance(assessment, Mapping):
                raise ReviewValidationError("Evidence assessment is invalid.")
            status = assessment.get("status")
            note = assessment.get("note", "")
            if status not in allowed_statuses or not isinstance(note, str):
                raise ReviewValidationError("Evidence assessment is invalid.")
            normalized_note = note.strip()
            if len(normalized_note) > 1_000:
                raise ReviewValidationError(
                    "Evidence assessment note cannot exceed 1000 characters."
                )
            if status == "NEEDS_CLARIFICATION" and len(normalized_note) < 10:
                raise ReviewValidationError(
                    "Clarification assessments require a short explanation."
                )
            result[media_id] = {"status": status, "note": normalized_note}
        return result

    @staticmethod
    def _validated_verdict_map(
        answers: Mapping[str, Mapping[str, object]],
    ) -> dict[str, dict[str, object]]:
        if len(answers) > 10:
            raise ReviewValidationError("A rubric can contain at most 10 conclusions.")
        outcomes = {
            "MEETS",
            "NEEDS_CLARIFICATION",
            "DOES_NOT_MEET",
            "NOT_APPLICABLE",
        }
        result: dict[str, dict[str, object]] = {}
        for key, answer in answers.items():
            if (
                not isinstance(key, str)
                or not key
                or len(key) > 64
                or not isinstance(answer, Mapping)
            ):
                raise ReviewValidationError("Criterion conclusion is invalid.")
            outcome = answer.get("outcome")
            rationale = answer.get("rationale")
            media_ids = answer.get("evidence_media_ids", [])
            if outcome not in outcomes:
                raise ReviewValidationError("Criterion conclusion is invalid.")
            if not isinstance(rationale, str) or len(rationale.strip()) > 2_000:
                raise ReviewValidationError(
                    "Criterion rationale cannot exceed 2000 characters."
                )
            if not isinstance(media_ids, (list, tuple)):
                raise ReviewValidationError("Criterion evidence is invalid.")
            parsed_ids = tuple(media_ids)
            if (
                len(parsed_ids) > 10
                or len(parsed_ids) != len(set(parsed_ids))
                or any(not isinstance(item, UUID) for item in parsed_ids)
            ):
                raise ReviewValidationError("Criterion evidence is invalid.")
            result[key] = {
                "outcome": outcome,
                "rationale": rationale.strip(),
                "evidence_media_ids": [str(item) for item in parsed_ids],
            }
        return result

    @staticmethod
    def _validated_answer_map(
        answers: Mapping[str, Mapping[str, object]],
        *,
        require_score: bool,
        evidence_required: bool,
    ) -> dict[str, dict[str, object]]:
        if len(answers) > 10:
            raise ReviewValidationError("A rubric can contain at most 10 answers.")
        result: dict[str, dict[str, object]] = {}
        for key, answer in answers.items():
            if (
                not isinstance(key, str)
                or not key
                or len(key) > 64
                or not isinstance(answer, Mapping)
            ):
                raise ReviewValidationError("Rubric answer is invalid.")
            rationale = answer.get("rationale")
            media_ids = answer.get("evidence_media_ids", [])
            if (
                not isinstance(rationale, str)
                or not 20 <= len(rationale.strip()) <= 2_000
            ):
                raise ReviewValidationError(
                    "Rubric rationale must contain 20 to 2000 characters."
                )
            if not isinstance(media_ids, (list, tuple)):
                raise ReviewValidationError("Rubric evidence is invalid.")
            parsed_ids = tuple(media_ids)
            if (
                len(parsed_ids) > 10
                or len(parsed_ids) != len(set(parsed_ids))
                or any(not isinstance(item, UUID) for item in parsed_ids)
            ):
                raise ReviewValidationError("Rubric evidence is invalid.")
            if evidence_required and not parsed_ids:
                raise ReviewValidationError("Specialist criteria require evidence.")
            normalized: dict[str, object] = {
                "rationale": rationale.strip(),
                "evidence_media_ids": [str(item) for item in parsed_ids],
            }
            if require_score:
                score = answer.get("score")
                if (
                    not isinstance(score, int)
                    or isinstance(score, bool)
                    or not 0 <= score <= 5
                ):
                    raise ReviewValidationError(
                        "Specialist score must be between 0 and 5."
                    )
                normalized["score"] = score
            else:
                outcome = answer.get("outcome")
                if outcome not in {"PASS", "FAIL", "NOT_APPLICABLE"}:
                    raise ReviewValidationError("Gate outcome is invalid.")
                normalized["outcome"] = outcome
            result[key] = normalized
        return result

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
        referenced.update(UUID(media_id) for media_id in draft.evidence_assessments)
        all_answers = (
            *draft.gate_answers.values(),
            *draft.specialist_answers.values(),
            *draft.criterion_verdicts.values(),
        )
        for answer in all_answers:
            raw_ids = answer.get("evidence_media_ids", [])
            if isinstance(raw_ids, (list, tuple)):
                referenced.update(UUID(str(media_id)) for media_id in raw_ids)
        if not referenced.issubset(allowed):
            raise ReviewValidationError(
                "Evidence references must belong to the locked dossier version."
            )

    @staticmethod
    def _validate_complete_evidence_assessments(
        review: Review,
        snapshot: Mapping[str, object],
    ) -> None:
        if snapshot.get("schemaVersion") != 2:
            return
        raw_evidences = snapshot.get("evidences")
        if not isinstance(raw_evidences, list):
            raise ReviewValidationError("Stored dossier evidence is invalid.")
        expected = {
            str(evidence["mediaAssetId"])
            for evidence in raw_evidences
            if isinstance(evidence, Mapping)
            and isinstance(evidence.get("mediaAssetId"), str)
        }
        assessments = review.evidence_assessments or {}
        assessed = {
            media_id
            for media_id, assessment in assessments.items()
            if isinstance(assessment, Mapping)
            and assessment.get("status")
            in {"VALID", "NEEDS_CLARIFICATION", "NOT_RELEVANT"}
        }
        if assessed != expected:
            raise ReviewValidationError(
                "Every file in this dossier version must be assessed before submission."
            )

    @staticmethod
    def _rubric_from_snapshot(
        snapshot: Mapping[str, object],
    ) -> Mapping[str, object] | None:
        dossier = snapshot.get("dossier")
        if not isinstance(dossier, Mapping):
            return None
        dossier_type = dossier.get("dossierType")
        if not isinstance(dossier_type, Mapping):
            return None
        rubric = dossier_type.get("reviewRubric")
        return rubric if isinstance(rubric, Mapping) else None

    @staticmethod
    def _is_verdict_rubric(rubric: Mapping[str, object] | None) -> bool:
        return rubric is not None and rubric.get("assessmentMethod") == "VERDICT"

    @classmethod
    def _validate_specialist_answers(
        cls, draft: ReviewDraft, snapshot: Mapping[str, object]
    ) -> None:
        rubric = cls._rubric_from_snapshot(snapshot)
        if rubric is None:
            if (
                draft.gate_answers
                or draft.specialist_answers
                or draft.criterion_verdicts
            ):
                raise ReviewValidationError(
                    "This dossier version has no specialist rubric."
                )
            return
        gates = rubric.get("gates", [])
        criteria = rubric.get("criteria", [])
        gate_keys = (
            {
                str(item["key"])
                for item in gates
                if isinstance(item, Mapping) and isinstance(item.get("key"), str)
            }
            if isinstance(gates, list)
            else set()
        )
        criterion_keys = (
            {
                str(item["key"])
                for item in criteria
                if isinstance(item, Mapping) and isinstance(item.get("key"), str)
            }
            if isinstance(criteria, list)
            else set()
        )
        answer_keys = (
            set(draft.criterion_verdicts)
            if cls._is_verdict_rubric(rubric)
            else set(draft.specialist_answers)
        )
        if set(draft.gate_answers) - gate_keys or answer_keys - criterion_keys:
            raise ReviewValidationError(
                "Rubric answer key does not belong to this dossier type version."
            )
        if cls._is_verdict_rubric(rubric) and draft.specialist_answers:
            raise ReviewValidationError("Verdict rubrics do not accept scores.")
        if not cls._is_verdict_rubric(rubric) and draft.criterion_verdicts:
            raise ReviewValidationError("Scored rubrics do not accept conclusions.")

    @staticmethod
    def _specialist_score(
        review: Review,
        rubric: Mapping[str, object] | None,
        *,
        require_complete: bool,
    ) -> int | None:
        if rubric is None:
            return None
        if rubric.get("assessmentMethod") == "VERDICT":
            return None
        raw_criteria = rubric.get("criteria")
        if not isinstance(raw_criteria, list):
            raise ReviewValidationError("Stored specialist rubric is invalid.")
        keys = [str(item["key"]) for item in raw_criteria if isinstance(item, Mapping)]
        if set(review.specialist_answers) != set(keys):
            if require_complete:
                raise ReviewValidationError(
                    "All specialist rubric criteria are required."
                )
            return None
        weighted = 0.0
        for criterion in raw_criteria:
            if not isinstance(criterion, Mapping):
                raise ReviewValidationError("Stored specialist rubric is invalid.")
            answer = review.specialist_answers.get(str(criterion["key"]))
            if not isinstance(answer, Mapping):
                raise ReviewValidationError("Stored specialist answer is invalid.")
            score = answer.get("score")
            weight = criterion.get("weight")
            if (
                not isinstance(score, int)
                or isinstance(score, bool)
                or not 0 <= score <= 5
                or not isinstance(weight, int)
                or isinstance(weight, bool)
                or not 0 <= weight <= 100
            ):
                raise ReviewValidationError("Stored specialist rubric is invalid.")
            weighted += score * weight / 5
        return round(weighted)

    @staticmethod
    def _validate_specialist_decision(
        review: Review, rubric: Mapping[str, object] | None
    ) -> None:
        if rubric is None:
            return
        gates = rubric.get("gates", [])
        if not isinstance(gates, list):
            raise ReviewValidationError("Stored specialist rubric is invalid.")
        gate_keys = {str(item["key"]) for item in gates if isinstance(item, Mapping)}
        if set(review.gate_answers) != gate_keys:
            raise ReviewValidationError("All mandatory rubric gates are required.")
        if review.recommendation is ReviewRecommendation.APPROVE:
            for gate in gates:
                if (
                    not isinstance(gate, Mapping)
                    or gate.get("required", True) is not True
                ):
                    continue
                answer = review.gate_answers.get(str(gate["key"]), {})
                if answer.get("outcome") != "PASS":
                    raise ReviewValidationError(
                        "Every required rubric gate must pass before approval."
                    )
            thresholds = rubric.get("thresholds")
            if not isinstance(thresholds, Mapping) or review.specialist_score is None:
                raise ReviewValidationError(
                    "Stored specialist rubric threshold is invalid."
                )
            if review.specialist_score < int(thresholds["approveMin"]):
                raise ReviewValidationError(
                    "Specialist score is below the approval threshold."
                )

    @staticmethod
    def _validate_verdict_decision(
        review: Review, rubric: Mapping[str, object]
    ) -> None:
        raw_criteria = rubric.get("criteria")
        gates = rubric.get("gates", [])
        if not isinstance(raw_criteria, list) or not isinstance(gates, list):
            raise ReviewValidationError("Stored verdict rubric is invalid.")
        criterion_keys = {
            str(item["key"]) for item in raw_criteria if isinstance(item, Mapping)
        }
        criterion_verdicts = review.criterion_verdicts or {}
        if set(criterion_verdicts) != criterion_keys:
            raise ReviewValidationError("Every rubric criterion requires a conclusion.")
        for answer in criterion_verdicts.values():
            if not isinstance(answer, Mapping):
                raise ReviewValidationError("Stored criterion conclusion is invalid.")
            rationale = answer.get("rationale")
            evidence_ids = answer.get("evidence_media_ids", [])
            outcome = answer.get("outcome")
            if not isinstance(rationale, str) or len(rationale.strip()) < 20:
                raise ReviewValidationError(
                    "Every rubric criterion requires a clear rationale."
                )
            if outcome != "NOT_APPLICABLE" and not evidence_ids:
                raise ReviewValidationError(
                    "Every applicable rubric criterion requires evidence."
                )
        outcomes = {
            str(value.get("outcome"))
            for value in criterion_verdicts.values()
            if isinstance(value, Mapping)
        }
        if not outcomes or outcomes == {"NOT_APPLICABLE"}:
            raise ReviewValidationError("At least one rubric criterion must apply.")
        gate_keys = {str(item["key"]) for item in gates if isinstance(item, Mapping)}
        gate_answers = review.gate_answers or {}
        if set(gate_answers) != gate_keys:
            raise ReviewValidationError("All mandatory rubric gates are required.")
        required_gate_failed = any(
            isinstance(gate, Mapping)
            and gate.get("required", True) is True
            and gate_answers.get(str(gate["key"]), {}).get("outcome") != "PASS"
            for gate in gates
        )
        expected = ReviewRecommendation.APPROVE
        if required_gate_failed or "DOES_NOT_MEET" in outcomes:
            expected = ReviewRecommendation.REJECT
        elif "NEEDS_CLARIFICATION" in outcomes:
            expected = ReviewRecommendation.SUPPLEMENT
        if review.recommendation is not expected:
            raise ReviewValidationError(
                f"Criterion conclusions require recommendation {expected.value}."
            )
        if expected in {
            ReviewRecommendation.SUPPLEMENT,
            ReviewRecommendation.REJECT,
        } and (
            review.applicant_feedback is None
            or len(review.applicant_feedback.strip()) < 20
        ):
            raise ReviewValidationError(
                "A clear applicant-facing explanation is required."
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
        review.gate_answers = {
            key: dict(value) for key, value in draft.gate_answers.items()
        }
        review.specialist_answers = {
            key: dict(value) for key, value in draft.specialist_answers.items()
        }
        review.criterion_verdicts = {
            key: dict(value) for key, value in draft.criterion_verdicts.items()
        }
        review.evidence_assessments = {
            key: dict(value) for key, value in draft.evidence_assessments.items()
        }
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
            len(review.criterion_comments[criterion].strip()) < 20
            for criterion in CRITERIA
        ):
            raise ReviewValidationError(
                "A rationale of at least 20 characters is required for every "
                "5T criterion."
            )
        criterion_evidence = cls._criterion_evidence_from_review(review)
        if set(criterion_evidence) != set(CRITERIA) or any(
            not criterion_evidence[criterion] for criterion in CRITERIA
        ):
            raise ReviewValidationError(
                "At least one evidence reference is required for every 5T criterion."
            )
        if not REVIEW_CHECKLIST_KEYS.issubset(review.checklist_answers) or not all(
            review.checklist_answers[key] for key in REVIEW_CHECKLIST_KEYS
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
            if sum(scores) < 75:
                raise ReviewValidationError(
                    "Approval recommendation requires a total score of at least 75."
                )
            if any(score < 12 for score in scores):
                raise ReviewValidationError(
                    "Approval recommendation requires every 5T score to be at least 12."
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
            rubric_version=review.rubric_version,
            specialist_score=review.specialist_score,
            recommendation=review.recommendation,
            criterion_comments=dict(review.criterion_comments),
            criterion_evidence=ReviewService._criterion_evidence_from_review(review),
            findings=ReviewService._findings_from_review(review),
            checklist_answers=dict(review.checklist_answers),
            applicant_feedback=review.applicant_feedback,
            private_note=review.private_note,
            gate_answers=review.gate_answers,
            specialist_answers=review.specialist_answers,
            criterion_verdicts=review.criterion_verdicts,
            evidence_assessments=review.evidence_assessments,
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
