import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierStatus,
    DossierVersion,
)
from app.modules.reviews.errors import (
    ReviewConflictError,
    ReviewNotFoundError,
    ReviewValidationError,
)
from app.modules.reviews.models import (
    ReviewAssignment,
    ReviewAssignmentStatus,
    ReviewRecommendation,
)
from app.modules.reviews.service import ReviewService
from app.modules.reviews.types import ReviewDraft

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)
OUTBOX_KEY = b"review-outbox-encryption-key!!!!"
COMMENTS = {
    "truth": "Tài sản và chứng cứ tồn tại.",
    "transparency": "Nguồn dữ liệu truy xuất rõ ràng.",
    "ownership": "Chủ thể có căn cứ phù hợp.",
    "professionalism": "Hồ sơ được trình bày chuyên nghiệp.",
    "respect": "Không phát hiện vi phạm bên thứ ba.",
}


async def _setup() -> tuple[
    ReviewService,
    AsyncEngine,
    dict[str, User],
    ReviewAssignment,
    ReviewAssignment,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    users = {
        name: User(
            id=uuid4(),
            email=f"{name}@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        for name in ("owner", "reviewer", "other")
    }
    category = Category(id=uuid4(), code="ASSET", name="Tài sản")
    dossier = Dossier(
        id=uuid4(),
        code="TMI-2026-SCORE0000001",
        owner_user_id=users["owner"].id,
        category_id=category.id,
        title="Hồ sơ chấm điểm 5T",
        current_version_no=1,
        submitted_at=NOW,
    )
    dossier._set_status_from_workflow(DossierStatus.UNDER_REVIEW)
    version = DossierVersion(
        id=uuid4(),
        dossier_id=dossier.id,
        version_no=1,
        snapshot_json={
            "schemaVersion": 1,
            "dossier": {
                "id": str(dossier.id),
                "code": dossier.code,
                "title": dossier.title,
            },
            "evidences": [
                {
                    "id": str(uuid4()),
                    "mediaAssetId": str(uuid4()),
                    "title": "Bản gốc",
                    "media": {
                        "mimeType": "application/pdf",
                        "bytes": 1024,
                        "sha256": "a" * 64,
                    },
                }
            ],
        },
        canonical_hash="b" * 64,
        submitted_by=users["owner"].id,
        submitted_at=NOW,
    )
    assignment = ReviewAssignment(
        id=uuid4(),
        dossier_id=dossier.id,
        dossier_version_id=version.id,
        reviewer_user_id=users["reviewer"].id,
        assigned_by=users["owner"].id,
        status=ReviewAssignmentStatus.ASSIGNED,
    )
    conflicted_assignment = ReviewAssignment(
        id=uuid4(),
        dossier_id=dossier.id,
        dossier_version_id=version.id,
        reviewer_user_id=users["other"].id,
        assigned_by=users["owner"].id,
        status=ReviewAssignmentStatus.ASSIGNED,
    )
    async with session_factory() as session:
        session.add_all(
            [
                *users.values(),
                category,
                dossier,
                version,
                assignment,
                conflicted_assignment,
            ]
        )
        await session.commit()

    service = ReviewService(
        session=session_factory(),
        payload_cipher=OutboxPayloadCipher(
            key=OUTBOX_KEY,
            key_id="test-review-key",
        ),
        clock=lambda: NOW,
    )
    return service, engine, users, assignment, conflicted_assignment


def _principal(user: User, role: str = "REVIEWER") -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=(role,),
    )


def test_reviewer_conflict_gate_draft_and_immutable_submit() -> None:
    async def exercise() -> None:
        service, engine, users, assignment, _ = await _setup()
        reviewer = _principal(users["reviewer"])

        page = await service.list_assignments(
            reviewer,
            status=None,
            page=1,
            page_size=20,
        )
        redacted = await service.get_assignment(reviewer, assignment.id)
        assert page.total == 1
        assert page.items[0].dossier_title == "Hồ sơ chấm điểm 5T"
        assert redacted.snapshot_json is None
        assert redacted.review is None

        acknowledged = await service.declare_conflict(
            reviewer,
            assignment.id,
            has_conflict=False,
            reason=None,
        )
        detail = await service.get_assignment(reviewer, assignment.id)
        assert acknowledged.status is ReviewAssignmentStatus.IN_PROGRESS
        assert detail.snapshot_json is not None

        incomplete = await service.save_draft(
            reviewer,
            assignment.id,
            ReviewDraft(
                truth_score=20,
                criterion_comments={"truth": COMMENTS["truth"]},
            ),
        )
        assert incomplete.truth_score == 20
        assert incomplete.total_score is None

        with pytest.raises(ReviewValidationError):
            await service.save_draft(
                reviewer,
                assignment.id,
                ReviewDraft(truth_score=21),
            )

        completed = await service.save_draft(
            reviewer,
            assignment.id,
            ReviewDraft(
                truth_score=18,
                transparency_score=17,
                ownership_score=16,
                professionalism_score=15,
                respect_score=14,
                criterion_comments=COMMENTS,
                recommendation=ReviewRecommendation.APPROVE,
                private_note="Đủ căn cứ chuyển hội đồng.",
            ),
        )
        assert completed.total_score == 80

        submitted = await service.submit_review(reviewer, assignment.id)
        assert submitted.submitted_at == NOW
        assert submitted.total_score == 80
        final_detail = await service.get_assignment(reviewer, assignment.id)
        assert final_detail.assignment.status is ReviewAssignmentStatus.SUBMITTED

        with pytest.raises(ReviewConflictError):
            await service.save_draft(
                reviewer,
                assignment.id,
                ReviewDraft(truth_score=10),
            )
        with pytest.raises(ReviewConflictError):
            await service.submit_review(reviewer, assignment.id)

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_reviewer_access_and_conflict_rules_are_enforced() -> None:
    async def exercise() -> None:
        service, engine, users, assignment, conflicted_assignment = await _setup()

        with pytest.raises(ReviewNotFoundError):
            await service.get_assignment(
                _principal(users["other"]),
                assignment.id,
            )
        with pytest.raises(ReviewValidationError):
            await service.declare_conflict(
                _principal(users["other"]),
                conflicted_assignment.id,
                has_conflict=True,
                reason=" ",
            )

        conflicted = await service.declare_conflict(
            _principal(users["other"]),
            conflicted_assignment.id,
            has_conflict=True,
            reason="Có quan hệ tư vấn với chủ hồ sơ.",
        )
        assert conflicted.status is ReviewAssignmentStatus.CONFLICTED
        detail = await service.get_assignment(
            _principal(users["other"]),
            conflicted_assignment.id,
        )
        assert detail.snapshot_json is None

        with pytest.raises(ReviewConflictError):
            await service.save_draft(
                _principal(users["other"]),
                conflicted_assignment.id,
                ReviewDraft(truth_score=10),
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
