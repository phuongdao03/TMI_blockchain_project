import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierEvidence,
    DossierStatus,
    DossierVersion,
)
from app.modules.media.errors import MediaForbiddenError
from app.modules.media.gateway import (
    ProviderAssetMetadata,
    StoredEncryptedAsset,
    UploadAuthorization,
)
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.service import MediaService
from app.modules.reviews.media_access import ReviewMediaAccessPolicy
from app.modules.reviews.models import (
    ReviewAssignment,
    ReviewAssignmentStatus,
    SimilarityCaseStatus,
    SimilarityReviewCase,
    SimilaritySignalType,
)

NOW = datetime(2026, 8, 2, 8, 0, tzinfo=UTC)


class ReviewDeliveryGateway:
    async def create_upload_signature(
        self,
        *,
        public_id: str,
        resource_type: str,
        timestamp: int,
        allowed_format: str,
    ) -> UploadAuthorization:
        raise AssertionError("Upload is outside this delivery test.")

    def verify_upload_result(
        self,
        *,
        public_id: str,
        version: int,
        signature: str,
    ) -> bool:
        raise AssertionError("Upload is outside this delivery test.")

    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> ProviderAssetMetadata:
        raise AssertionError("Upload is outside this delivery test.")

    async def download_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        max_bytes: int,
    ) -> bytes:
        raise AssertionError("Inspection is outside this delivery test.")

    async def upload_encrypted_asset(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredEncryptedAsset:
        raise AssertionError("Encryption is outside this delivery test.")

    def create_signed_delivery_url(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        expires_at: int,
    ) -> str:
        return f"https://media.test/evidence?expires_at={expires_at}"

    async def close(self) -> None:
        return None

    async def delete_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> None:
        raise AssertionError("Delete is outside this delivery test.")


def _principal(user: User, role: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=(role,),
    )


def test_delivery_requires_acknowledged_owned_assignment() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        owner = User(
            id=uuid4(),
            email="owner-review-media@tmigroup.vn",
            password_hash="unused",
            status=UserStatus.ACTIVE,
        )
        reviewer = User(
            id=uuid4(),
            email="reviewer-media@tmigroup.vn",
            password_hash="unused",
            status=UserStatus.ACTIVE,
        )
        other = User(
            id=uuid4(),
            email="other-reviewer-media@tmigroup.vn",
            password_hash="unused",
            status=UserStatus.ACTIVE,
        )
        category = Category(
            id=uuid4(),
            code="MEDIA_REVIEW",
            name="Review media",
            is_active=True,
        )
        dossier = Dossier(
            id=uuid4(),
            code="HS-2026-MEDIA01",
            owner_user_id=owner.id,
            category_id=category.id,
            title="Hồ sơ có bằng chứng",
        )
        dossier._set_status_from_workflow(DossierStatus.UNDER_REVIEW)
        version = DossierVersion(
            id=uuid4(),
            dossier_id=dossier.id,
            version_no=1,
            snapshot_json={"schemaVersion": 1},
            canonical_hash="a" * 64,
            submitted_by=owner.id,
            submitted_at=NOW,
        )
        comparison_version = DossierVersion(
            id=uuid4(),
            dossier_id=dossier.id,
            version_no=2,
            snapshot_json={"schemaVersion": 1},
            canonical_hash="b" * 64,
            submitted_by=owner.id,
            submitted_at=NOW,
        )
        asset = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id="ip-certificate/local/evidence/review",
            resource_type="image",
            access_mode="authenticated",
            original_filename="evidence.png",
            mime_type="image/png",
            bytes=2_048,
            status=MediaStatus.ACTIVE,
        )
        evidence = DossierEvidence(
            id=uuid4(),
            dossier_id=dossier.id,
            dossier_version_id=version.id,
            media_asset_id=asset.id,
            evidence_type="OWNERSHIP",
            title="Bằng chứng",
        )
        assignment = ReviewAssignment(
            id=uuid4(),
            dossier_id=dossier.id,
            dossier_version_id=version.id,
            reviewer_user_id=reviewer.id,
            assigned_by=owner.id,
            status=ReviewAssignmentStatus.ASSIGNED,
        )
        async with sessions() as session:
            session.add_all(
                [
                    owner,
                    reviewer,
                    other,
                    category,
                    dossier,
                    version,
                    comparison_version,
                    asset,
                    evidence,
                    assignment,
                ]
            )
            await session.commit()

        session = sessions()
        service = MediaService(
            session=session,
            gateway=ReviewDeliveryGateway(),
            environment="local",
            signature_ttl_seconds=3_600,
            delivery_ttl_seconds=300,
            avatar_max_bytes=5_242_880,
            evidence_max_bytes=20_971_520,
            delivery_access_policy=ReviewMediaAccessPolicy(session),
            clock=lambda: NOW,
        )
        reviewer_principal = _principal(reviewer, "REVIEWER")
        with pytest.raises(MediaForbiddenError):
            await service.create_signed_url(reviewer_principal, asset.id)

        async with sessions() as update_session:
            stored = await update_session.get(ReviewAssignment, assignment.id)
            assert stored is not None
            stored.status = ReviewAssignmentStatus.IN_PROGRESS
            await update_session.commit()

        delivery = await service.create_signed_url(reviewer_principal, asset.id)
        assert "expires_at=" in delivery.url

        with pytest.raises(MediaForbiddenError):
            await service.create_signed_url(
                _principal(other, "REVIEWER"),
                asset.id,
            )
        async with sessions() as update_session:
            update_session.add(
                SimilarityReviewCase(
                    id=uuid4(),
                    left_dossier_version_id=version.id,
                    right_dossier_version_id=comparison_version.id,
                    signal_type=SimilaritySignalType.TEXT,
                    text_score=0.91,
                    image_distance=None,
                    policy_version="near-duplicate-v1",
                    status=SimilarityCaseStatus.ASSIGNED,
                    assigned_reviewer_user_id=other.id,
                    assigned_by=owner.id,
                    assigned_at=NOW,
                    created_at=NOW,
                )
            )
            await update_session.commit()
        similarity_delivery = await service.create_signed_url(
            _principal(other, "REVIEWER"),
            asset.id,
        )
        assert "expires_at=" in similarity_delivery.url
        owner_delivery = await service.create_signed_url(
            _principal(owner, "APPLICANT"),
            asset.id,
        )
        assert owner_delivery.expires_at == int(NOW.timestamp()) + 300

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
