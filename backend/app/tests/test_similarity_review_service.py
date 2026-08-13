import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category, Dossier, DossierVersion
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.reviews.errors import (
    ReviewConflictError,
    ReviewForbiddenError,
    ReviewValidationError,
)
from app.modules.reviews.models import (
    SimilarityCaseDisposition,
    SimilarityCaseStatus,
    SimilarityReviewCase,
)
from app.modules.reviews.similarity_service import SimilarityReviewService

NOW = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)


def _principal(user: User, *roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=roles,
    )


def test_similarity_case_assignment_resolution_authorization_and_audit() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        admin = User(
            id=uuid4(), email="admin@tmigroup.vn",
            password_hash="unused", status=UserStatus.ACTIVE,
        )
        reviewer = User(
            id=uuid4(), email="reviewer@tmigroup.vn",
            password_hash="unused", status=UserStatus.ACTIVE,
        )
        outsider = User(
            id=uuid4(), email="outsider@tmigroup.vn",
            password_hash="unused", status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="ART", name="Artwork")
        versions: list[DossierVersion] = []
        rows: list[object] = [admin, reviewer, outsider, category]
        for index, owner in enumerate((admin, outsider), start=1):
            dossier = Dossier(
                id=uuid4(), code=f"DOS-{index}", owner_user_id=owner.id,
                category_id=category.id, title=f"Artwork {index}",
            )
            version = DossierVersion(
                id=uuid4(), dossier_id=dossier.id, version_no=1,
                snapshot_json={
                    "schemaVersion": 1,
                    "dossier": {"code": dossier.code, "title": dossier.title},
                    "evidences": [{"mediaAssetId": str(uuid4())}],
                },
                canonical_hash=f"{index}" * 64,
                submitted_by=owner.id,
            )
            versions.append(version)
            rows.extend((dossier, version))
        reviewer_role = Role(id=uuid4(), code="REVIEWER")
        rows.extend(
            (
                reviewer_role,
                UserRole(user_id=reviewer.id, role_id=reviewer_role.id),
            )
        )
        async with sessions() as session:
            session.add_all(rows)
            await session.commit()

        service = SimilarityReviewService(session=sessions(), clock=lambda: NOW)
        created = await service.record_text_candidate(
            versions[1].id,
            versions[0].id,
            score=0.91,
            policy_version="near-duplicate-v1",
        )
        replay = await service.record_text_candidate(
            versions[0].id,
            versions[1].id,
            score=0.91,
            policy_version="near-duplicate-v1",
        )
        assert replay.id == created.id
        assert created.status is SimilarityCaseStatus.OPEN
        assert (
            created.left_dossier_version_id.int
            < created.right_dossier_version_id.int
        )

        admin_page = await service.list_admin_cases(
            _principal(admin, "SUPER_ADMIN"),
            status=SimilarityCaseStatus.OPEN,
            page=1,
            page_size=20,
        )
        assert admin_page.total == 1
        assert admin_page.items[0].left_asset is not None
        assert admin_page.items[0].right_asset is not None
        assert admin_page.items[0].left_asset.evidence_media_ids

        with pytest.raises(ReviewForbiddenError):
            await service.assign_case(
                _principal(outsider, "APPLICANT"), created.id, reviewer.id
            )
        assigned = await service.assign_case(
            _principal(admin, "SUPER_ADMIN"), created.id, reviewer.id
        )
        assert assigned.status is SimilarityCaseStatus.ASSIGNED
        page = await service.list_reviewer_cases(
            _principal(reviewer, "REVIEWER"),
            status=SimilarityCaseStatus.ASSIGNED,
            page=1,
            page_size=20,
        )
        assert page.total == 1
        assert page.items[0].id == created.id
        with pytest.raises(ReviewForbiddenError):
            await service.list_reviewer_cases(
                _principal(outsider, "APPLICANT"),
                status=None,
                page=1,
                page_size=20,
            )

        with pytest.raises(ReviewForbiddenError):
            await service.resolve_case(
                _principal(outsider, "REVIEWER"),
                created.id,
                disposition=SimilarityCaseDisposition.DISTINCT,
                reason="These works are clearly different after comparison.",
            )
        with pytest.raises(ReviewValidationError):
            await service.resolve_case(
                _principal(reviewer, "REVIEWER"),
                created.id,
                disposition=SimilarityCaseDisposition.DISTINCT,
                reason="Too short",
            )
        resolved = await service.resolve_case(
            _principal(reviewer, "REVIEWER"),
            created.id,
            disposition=SimilarityCaseDisposition.RELATED,
            reason="The works share a series identity but are separate submissions.",
        )
        assert resolved.status is SimilarityCaseStatus.RESOLVED
        assert resolved.disposition is SimilarityCaseDisposition.RELATED

        with pytest.raises(ReviewConflictError):
            await service.resolve_case(
                _principal(reviewer, "REVIEWER"),
                created.id,
                disposition=SimilarityCaseDisposition.SAME_WORK,
                reason="A resolved disposition cannot be silently replaced later.",
            )
        async with sessions() as session:
            actions = tuple(
                (await session.scalars(select(AuditLog.action))).all()
            )
            assert actions == (
                "similarity.case.assigned",
                "similarity.case.resolved",
            )
            assert await session.scalar(
                select(func.count()).select_from(AuditLog)
            ) == 2

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_concurrent_candidate_creation_converges_to_one_case(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'race.db').as_posix()}"
        )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        first_version_id = uuid4()
        second_version_id = uuid4()

        async def create_with_lock_retry() -> object:
            for _ in range(5):
                service = SimilarityReviewService(session=sessions(), clock=lambda: NOW)
                try:
                    result = await service.record_text_candidate(
                        first_version_id,
                        second_version_id,
                        score=0.91,
                        policy_version="near-duplicate-v1",
                    )
                    await service.close()
                    return result.id
                except OperationalError:
                    await service.close()
                    await asyncio.sleep(0.01)
            raise AssertionError("Concurrent candidate creation did not converge.")

        results = await asyncio.gather(
            create_with_lock_retry(),
            create_with_lock_retry(),
        )
        assert results[0] == results[1]
        async with sessions() as session:
            count = await session.scalar(
                select(func.count()).select_from(SimilarityReviewCase)
            )
            assert count == 1
        await engine.dispose()

    asyncio.run(exercise())
