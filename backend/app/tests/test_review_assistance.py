# ruff: noqa: E501

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category, Dossier, DossierStatus, DossierVersion
from app.modules.reviews.errors import (
    ReviewConflictError,
    ReviewForbiddenError,
    ReviewNotFoundError,
)
from app.modules.reviews.models import (
    ReviewAssignment,
    ReviewAssignmentStatus,
    ReviewAssistanceRequest,
    ReviewAssistanceRequestStatus,
)
from app.modules.reviews.service import ReviewService

NOW = datetime(2026, 9, 21, 8, 0, tzinfo=UTC)
OUTBOX_KEY = b"review-assistance-outbox-key!!!!"


async def _setup() -> tuple[
    ReviewService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    dict[str, User],
    Dossier,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    users = {
        name: User(
            id=uuid4(),
            email=f"{name}@cnsgroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        for name in ("owner", "admin", "reviewer", "reviewer_two", "member")
    }
    category = Category(id=uuid4(), code="ASSET", name="TÃ i sáº£n")
    dossier = Dossier(
        id=uuid4(),
        code="CNS-2026-ASSIST00001",
        owner_user_id=users["owner"].id,
        category_id=category.id,
        title="Há»“ sÆ¡ cáº§n thÃªm chuyÃªn gia thÄ©nh Ä‘á»‹nh",
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
            "dossier": {"title": dossier.title, "code": dossier.code},
            "evidences": [],
        },
        canonical_hash="a" * 64,
        submitted_by=users["owner"].id,
        submitted_at=NOW,
    )
    moderator_role = Role(id=uuid4(), code="MODERATOR")
    async with session_factory() as session:
        session.add_all(
            [
                *users.values(),
                category,
                dossier,
                version,
                moderator_role,
                UserRole(user_id=users["reviewer"].id, role_id=moderator_role.id),
                UserRole(
                    user_id=users["reviewer_two"].id,
                    role_id=moderator_role.id,
                ),
            ]
        )
        await session.commit()

    return (
        ReviewService(
            session=session_factory(),
            payload_cipher=OutboxPayloadCipher(
                key=OUTBOX_KEY,
                key_id="test-review-assistance-key",
            ),
            clock=lambda: NOW,
        ),
        session_factory,
        engine,
        users,
        dossier,
    )


def _principal(user: User, *roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=roles,
    )


def test_assignment_owner_requests_help_and_admin_approves_atomically() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, dossier = await _setup()
        admin = _principal(users["admin"], "SUPER_ADMIN")
        reviewer = _principal(users["reviewer"], "MODERATOR")
        original = (
            await service.assign_reviewers(
                admin,
                dossier.id,
                reviewer_user_ids=(users["reviewer"].id,),
                due_at=NOW + timedelta(days=5),
            )
        )[0]

        request = await service.request_assistance(
            reviewer,
            original.id,
            reason="Há»“ sÆ¡ cÃ³ nhiá»u phá»¥ lá»¥c chuyÃªn ngÃ nh, cáº§n thÃªm ngÆ°á»i Ä‘á»‘i chiáº¿u.",
            requested_reviewer_count=1,
        )

        assert request.status is ReviewAssistanceRequestStatus.PENDING
        assert request.assignment_id == original.id
        assert request.requested_by_user_id == users["reviewer"].id

        approved = await service.approve_assistance_request(
            admin,
            request.id,
            reviewer_user_ids=(users["reviewer_two"].id,),
            due_at=NOW + timedelta(days=4),
        )

        assert approved.status is ReviewAssistanceRequestStatus.APPROVED
        assert approved.reviewed_by_user_id == users["admin"].id

        async with session_factory() as session:
            requests = tuple(
                (await session.scalars(select(ReviewAssistanceRequest))).all()
            )
            assignments = tuple((await session.scalars(select(ReviewAssignment))).all())
            audit_actions = tuple(
                (await session.scalars(select(AuditLog.action))).all()
            )
            assert len(requests) == 1
            assert {item.reviewer_user_id for item in assignments} == {
                users["reviewer"].id,
                users["reviewer_two"].id,
            }
            assert all(
                item.status is ReviewAssignmentStatus.IN_PROGRESS
                for item in assignments
            )
            assert "review.assistance_requested" in audit_actions
            assert "review.assistance_approved" in audit_actions
            assert (
                await session.scalar(select(func.count()).select_from(OutboxEvent)) == 4
            )

        with pytest.raises(ReviewConflictError):
            await service.approve_assistance_request(
                admin,
                request.id,
                reviewer_user_ids=(users["reviewer_two"].id,),
                due_at=None,
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_request_requires_the_active_assignment_owner_and_single_pending_request() -> (
    None
):
    async def exercise() -> None:
        service, _, engine, users, dossier = await _setup()
        admin = _principal(users["admin"], "SUPER_ADMIN")
        original = (
            await service.assign_reviewers(
                admin,
                dossier.id,
                reviewer_user_ids=(users["reviewer"].id,),
                due_at=None,
            )
        )[0]

        with pytest.raises(ReviewNotFoundError):
            await service.request_assistance(
                _principal(users["reviewer_two"], "MODERATOR"),
                original.id,
                reason="Táº¡o yÃªu cáº§u thay ngÆ°á»i khÃ¡c lÃ  khÃ´ng Ä‘Æ°á»£c phÃ©p.",
                requested_reviewer_count=1,
            )

        await service.request_assistance(
            _principal(users["reviewer"], "MODERATOR"),
            original.id,
            reason="Cáº§n thÃªm chuyÃªn gia Ä‘á»ƒ kiá»ƒm tra nhá»¯ng pháº§n cÃ³ rá»§i ro cao.",
            requested_reviewer_count=1,
        )
        with pytest.raises(ReviewConflictError):
            await service.request_assistance(
                _principal(users["reviewer"], "MODERATOR"),
                original.id,
                reason="KhÃ´ng thá»ƒ má»Ÿ hai yÃªu cáº§u há»— trá»£ cÃ¹ng lÃºc cho má»™t phÃ¢n cÃ´ng.",
                requested_reviewer_count=1,
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_assistance_keeps_the_four_role_authorization_boundary() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, dossier = await _setup()
        admin = _principal(users["admin"], "SUPER_ADMIN")
        moderator = _principal(users["reviewer"], "MODERATOR")
        assignment = (
            await service.assign_reviewers(
                admin,
                dossier.id,
                reviewer_user_ids=(users["reviewer"].id,),
                due_at=None,
            )
        )[0]

        for role in ("VIEWER", "USER", "SUPER_ADMIN"):
            with pytest.raises(ReviewForbiddenError):
                await service.request_assistance(
                    _principal(users["member"], role),
                    assignment.id,
                    reason="Additional specialist capacity is needed for review.",
                    requested_reviewer_count=1,
                )

        request = await service.request_assistance(
            moderator,
            assignment.id,
            reason="Additional specialist capacity is needed for review.",
            requested_reviewer_count=1,
        )
        for role in ("VIEWER", "USER", "MODERATOR"):
            with pytest.raises(ReviewForbiddenError):
                await service.approve_assistance_request(
                    _principal(users["member"], role),
                    request.id,
                    reviewer_user_ids=(users["reviewer_two"].id,),
                    due_at=None,
                )
            with pytest.raises(ReviewForbiddenError):
                await service.decline_assistance_request(
                    _principal(users["member"], role),
                    request.id,
                    reason="Capacity remains allocated to other priority reviews.",
                )

        async with session_factory() as session:
            current = await session.get(ReviewAssignment, assignment.id)
            assert current is not None
            current.status = ReviewAssignmentStatus.SUBMITTED
            await session.commit()

        with pytest.raises(ReviewConflictError):
            await service.request_assistance(
                moderator,
                assignment.id,
                reason="Additional specialist capacity is needed for review.",
                requested_reviewer_count=1,
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
