from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.reviews.errors import (
    ReviewConflictError,
    ReviewForbiddenError,
    ReviewNotFoundError,
    ReviewValidationError,
)
from app.modules.reviews.models import (
    SimilarityCaseDisposition,
    SimilarityCaseStatus,
    SimilarityReviewCase,
    SimilaritySignalType,
)
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.types import (
    SimilarityAssetSummary,
    SimilarityCasePage,
    SimilarityCaseView,
)


class SimilarityReviewService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._session = session
        self._reviews = ReviewRepository(session)
        self._audit = AuditService(session)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    async def record_text_candidate(
        self,
        first_version_id: UUID,
        second_version_id: UUID,
        *,
        score: float,
        policy_version: str,
    ) -> SimilarityCaseView:
        if first_version_id == second_version_id:
            raise ReviewValidationError("Candidate versions must be different.")
        if not 0 <= score <= 1:
            raise ReviewValidationError("Text similarity score is invalid.")
        policy = self._policy_version(policy_version)
        left, right = sorted(
            (first_version_id, second_version_id),
            key=lambda value: value.int,
        )
        try:
            async with self._session.begin():
                existing = await self._reviews.find_similarity_case(
                    left_version_id=left,
                    right_version_id=right,
                    signal_type=SimilaritySignalType.TEXT,
                    policy_version=policy,
                )
                if existing is not None:
                    return self._view(existing)
                case = SimilarityReviewCase(
                    id=self._uuid_factory(),
                    left_dossier_version_id=left,
                    right_dossier_version_id=right,
                    signal_type=SimilaritySignalType.TEXT,
                    text_score=score,
                    image_distance=None,
                    policy_version=policy,
                    status=SimilarityCaseStatus.OPEN,
                    created_at=self._clock(),
                )
                self._reviews.add_similarity_case(case)
                await self._session.flush()
                return self._view(case)
        except IntegrityError:
            await self._session.rollback()
            async with self._session.begin():
                replay = await self._reviews.find_similarity_case(
                    left_version_id=left,
                    right_version_id=right,
                    signal_type=SimilaritySignalType.TEXT,
                    policy_version=policy,
                )
                if replay is None:
                    raise
                return self._view(replay)

    async def record_image_candidate(
        self,
        first_version_id: UUID,
        second_version_id: UUID,
        *,
        distance: int,
        policy_version: str,
    ) -> SimilarityCaseView:
        if first_version_id == second_version_id:
            raise ReviewValidationError("Candidate versions must be different.")
        if not 0 <= distance <= 64:
            raise ReviewValidationError("Image similarity distance is invalid.")
        policy = self._policy_version(policy_version)
        left, right = sorted(
            (first_version_id, second_version_id),
            key=lambda value: value.int,
        )
        try:
            async with self._session.begin():
                existing = await self._reviews.find_similarity_case(
                    left_version_id=left,
                    right_version_id=right,
                    signal_type=SimilaritySignalType.IMAGE,
                    policy_version=policy,
                )
                if existing is not None:
                    return self._view(existing)
                case = SimilarityReviewCase(
                    id=self._uuid_factory(),
                    left_dossier_version_id=left,
                    right_dossier_version_id=right,
                    signal_type=SimilaritySignalType.IMAGE,
                    text_score=None,
                    image_distance=distance,
                    policy_version=policy,
                    status=SimilarityCaseStatus.OPEN,
                    created_at=self._clock(),
                )
                self._reviews.add_similarity_case(case)
                await self._session.flush()
                return self._view(case)
        except IntegrityError:
            await self._session.rollback()
            async with self._session.begin():
                replay = await self._reviews.find_similarity_case(
                    left_version_id=left,
                    right_version_id=right,
                    signal_type=SimilaritySignalType.IMAGE,
                    policy_version=policy,
                )
                if replay is None:
                    raise
                return self._view(replay)

    async def assign_case(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        reviewer_user_id: UUID,
    ) -> SimilarityCaseView:
        self._require_admin(principal)
        async with self._session.begin():
            case = await self._reviews.get_similarity_case(case_id, for_update=True)
            if case is None:
                raise ReviewNotFoundError()
            if case.status is not SimilarityCaseStatus.OPEN:
                raise ReviewConflictError("Only an open case can be assigned.")
            reviewer = await self._reviews.get_active_reviewer(reviewer_user_id)
            if reviewer is None:
                raise ReviewValidationError("Reviewer is not active or eligible.")
            now = self._clock()
            case.assigned_reviewer_user_id = reviewer_user_id
            case.assigned_by = principal.user_id
            case.assigned_at = now
            case.status = SimilarityCaseStatus.ASSIGNED
            self._audit.record(
                actor_user_id=principal.user_id,
                action="similarity.case.assigned",
                resource_type="similarity_review_case",
                resource_id=str(case.id),
                after={"reviewerUserId": str(reviewer_user_id)},
            )
            await self._session.flush()
            return self._view(case)

    async def get_case(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
    ) -> SimilarityCaseView:
        self._require_reviewer(principal)
        async with self._session.begin():
            case = await self._reviews.get_similarity_case(
                case_id,
                reviewer_user_id=principal.user_id,
            )
            if case is None:
                raise ReviewNotFoundError()
            return self._view(case)

    async def list_reviewer_cases(
        self,
        principal: AuthPrincipal,
        *,
        status: SimilarityCaseStatus | None,
        page: int,
        page_size: int,
    ) -> SimilarityCasePage:
        self._require_reviewer(principal)
        if page < 1 or page_size < 1 or page_size > 100:
            raise ReviewValidationError("Similarity case pagination is invalid.")
        async with self._session.begin():
            rows, total = await self._reviews.list_similarity_cases(
                reviewer_user_id=principal.user_id,
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return SimilarityCasePage(
                items=tuple(self._view(case) for case in rows),
                total=total,
            )

    async def list_admin_cases(
        self,
        principal: AuthPrincipal,
        *,
        status: SimilarityCaseStatus | None,
        page: int,
        page_size: int,
    ) -> SimilarityCasePage:
        self._require_admin(principal)
        if page < 1 or page_size < 1 or page_size > 100:
            raise ReviewValidationError("Similarity case pagination is invalid.")
        async with self._session.begin():
            rows, total = await self._reviews.list_similarity_cases(
                reviewer_user_id=None,
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return SimilarityCasePage(
                items=tuple(self._view(case) for case in rows),
                total=total,
            )

    async def resolve_case(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        *,
        disposition: SimilarityCaseDisposition,
        reason: str,
    ) -> SimilarityCaseView:
        self._require_reviewer(principal)
        normalized_reason = " ".join(reason.split())
        if not 20 <= len(normalized_reason) <= 2_000:
            raise ReviewValidationError(
                "Resolution reason must contain between 20 and 2000 characters."
            )
        async with self._session.begin():
            case = await self._reviews.get_similarity_case(
                case_id,
                reviewer_user_id=principal.user_id,
                for_update=True,
            )
            if case is None:
                raise ReviewForbiddenError()
            if case.status is not SimilarityCaseStatus.ASSIGNED:
                raise ReviewConflictError("Only an assigned case can be resolved.")
            case.disposition = disposition
            case.resolution_reason = normalized_reason
            case.resolved_at = self._clock()
            case.status = SimilarityCaseStatus.RESOLVED
            self._audit.record(
                actor_user_id=principal.user_id,
                action="similarity.case.resolved",
                resource_type="similarity_review_case",
                resource_id=str(case.id),
                after={
                    "disposition": disposition.value,
                    "reason": normalized_reason,
                },
            )
            await self._session.flush()
            return self._view(case)

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="review.assign",
                compatible_roles=frozenset({"SUPER_ADMIN"}),
            ),
            ReviewForbiddenError,
        )

    @staticmethod
    def _require_reviewer(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="similarity.review",
                compatible_roles=frozenset({"REVIEWER"}),
                allow_super_admin=False,
            ),
            ReviewForbiddenError,
        )

    @staticmethod
    def _policy_version(value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 64:
            raise ReviewValidationError("Similarity policy version is invalid.")
        return normalized

    @staticmethod
    def _view(case: SimilarityReviewCase) -> SimilarityCaseView:
        return SimilarityCaseView(
            id=case.id,
            left_dossier_version_id=case.left_dossier_version_id,
            right_dossier_version_id=case.right_dossier_version_id,
            left_asset=SimilarityReviewService._asset_summary(
                case.__dict__.get("left_version")
            ),
            right_asset=SimilarityReviewService._asset_summary(
                case.__dict__.get("right_version")
            ),
            signal_type=case.signal_type,
            text_score=case.text_score,
            image_distance=case.image_distance,
            policy_version=case.policy_version,
            status=case.status,
            assigned_reviewer_user_id=case.assigned_reviewer_user_id,
            disposition=case.disposition,
            resolution_reason=case.resolution_reason,
            created_at=case.created_at,
            assigned_at=case.assigned_at,
            resolved_at=case.resolved_at,
        )

    @staticmethod
    def _asset_summary(version: object) -> SimilarityAssetSummary | None:
        from app.modules.dossiers.models import DossierVersion

        if not isinstance(version, DossierVersion):
            return None
        dossier = version.snapshot_json.get("dossier")
        if not isinstance(dossier, dict):
            return None
        code = dossier.get("code")
        title = dossier.get("title")
        if not isinstance(code, str) or not isinstance(title, str):
            return None
        evidence_media_ids: list[UUID] = []
        evidences = version.snapshot_json.get("evidences")
        if isinstance(evidences, list):
            for evidence in evidences:
                if not isinstance(evidence, dict):
                    continue
                media_id = evidence.get("mediaAssetId")
                if not isinstance(media_id, str):
                    continue
                try:
                    evidence_media_ids.append(UUID(media_id))
                except ValueError:
                    continue
        return SimilarityAssetSummary(
            dossier_id=version.dossier_id,
            dossier_code=code,
            dossier_title=title,
            version_no=version.version_no,
            evidence_media_ids=tuple(evidence_media_ids),
        )

    async def close(self) -> None:
        await self._session.close()
