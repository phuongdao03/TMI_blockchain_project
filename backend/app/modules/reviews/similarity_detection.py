from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dossiers.models import Dossier, DossierVersion
from app.modules.dossiers.similarity import (
    SimilarityInputError,
    SimilarityPolicy,
    normalized_text_similarity,
    perceptual_hash_distance,
)
from app.modules.reviews.similarity_service import SimilarityReviewService

MAX_COMPARISON_CANDIDATES = 500


class SimilarityDetectionService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        policy: SimilarityPolicy | None = None,
    ) -> None:
        self._session = session
        self._policy = policy or SimilarityPolicy()

    async def detect(self, dossier_version_id: UUID) -> None:
        async with self._session.begin():
            target = await self._session.get(DossierVersion, dossier_version_id)
            if target is None:
                return
            target_dossier = await self._session.get(Dossier, target.dossier_id)
            if target_dossier is None:
                return
            rows = await self._session.execute(
                select(DossierVersion, Dossier)
                .join(Dossier, Dossier.id == DossierVersion.dossier_id)
                .where(
                    DossierVersion.id != target.id,
                    Dossier.category_id == target_dossier.category_id,
                    Dossier.deleted_at.is_(None),
                )
                .order_by(
                    DossierVersion.submitted_at.desc(),
                    DossierVersion.id.desc(),
                )
                .limit(MAX_COMPARISON_CANDIDATES)
            )
            candidates = tuple(rows.tuples().all())

        review = SimilarityReviewService(session=self._session)
        target_title = self._title(target.snapshot_json)
        target_hashes = self._image_hashes(target.snapshot_json)
        for candidate, _ in candidates:
            score = normalized_text_similarity(
                target_title,
                self._title(candidate.snapshot_json),
            )
            if self._policy.text_is_candidate(score):
                await review.record_text_candidate(
                    target.id,
                    candidate.id,
                    score=score,
                    policy_version=self._policy.version,
                )
            distance = self._minimum_image_distance(
                target_hashes,
                self._image_hashes(candidate.snapshot_json),
            )
            if distance is not None and self._policy.image_is_candidate(distance):
                await review.record_image_candidate(
                    target.id,
                    candidate.id,
                    distance=distance,
                    policy_version=self._policy.version,
                )

    @staticmethod
    def _title(snapshot: Mapping[str, object]) -> str:
        dossier = snapshot.get("dossier")
        if not isinstance(dossier, dict):
            return ""
        title = dossier.get("title")
        return title if isinstance(title, str) else ""

    @staticmethod
    def _image_hashes(snapshot: Mapping[str, object]) -> tuple[str, ...]:
        evidences = snapshot.get("evidences")
        if not isinstance(evidences, list):
            return ()
        values: list[str] = []
        for evidence in evidences:
            if not isinstance(evidence, dict):
                continue
            media = evidence.get("media")
            if not isinstance(media, dict):
                continue
            value = media.get("perceptualHash")
            if isinstance(value, str):
                values.append(value)
        return tuple(values)

    @staticmethod
    def _minimum_image_distance(
        left: tuple[str, ...],
        right: tuple[str, ...],
    ) -> int | None:
        distances: list[int] = []
        for left_hash in left:
            for right_hash in right:
                try:
                    distances.append(
                        perceptual_hash_distance(left_hash, right_hash)
                    )
                except SimilarityInputError:
                    continue
        return min(distances) if distances else None

    async def close(self) -> None:
        await self._session.close()
