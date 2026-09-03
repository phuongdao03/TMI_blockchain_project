import asyncio
import json
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
from app.modules.auth.models import (
    Role,
    User,
    UserRole,
    UserStatus,
)
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
    ReviewForbiddenError,
    ReviewValidationError,
)
from app.modules.reviews.models import (
    ReviewAssignment,
    ReviewAssignmentStatus,
)
from app.modules.reviews.service import ReviewService

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)
OUTBOX_KEY = b"review-outbox-encryption-key!!!!"


async def _setup() -> tuple[
    ReviewService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    dict[str, User],
    Dossier,
    DossierVersion,
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
        for name in ("owner", "admin", "reviewer", "reviewer_two", "member")
    }
    category = Category(id=uuid4(), code="ASSET", name="Tài sản")
    dossier = Dossier(
        id=uuid4(),
        code="TMI-2026-REVIEW000001",
        owner_user_id=users["owner"].id,
        category_id=category.id,
        title="Hồ sơ chờ thẩm định",
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
    reviewer_role = Role(id=uuid4(), code="MODERATOR")
    async with session_factory() as session:
        session.add_all(
            [
                *users.values(),
                category,
                dossier,
                version,
                reviewer_role,
                UserRole(
                    user_id=users["reviewer"].id,
                    role_id=reviewer_role.id,
                ),
                UserRole(
                    user_id=users["reviewer_two"].id,
                    role_id=reviewer_role.id,
                ),
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
    return service, session_factory, engine, users, dossier, version


def _principal(user: User, *roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=roles,
    )


def test_admin_assigns_active_reviewers_and_emits_encrypted_events() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, dossier, version = await _setup()
        assignments = await service.assign_reviewers(
            _principal(users["admin"], "SUPER_ADMIN"),
            dossier.id,
            reviewer_user_ids=(
                users["reviewer"].id,
                users["reviewer_two"].id,
            ),
            due_at=NOW + timedelta(days=5),
        )

        assert len(assignments) == 2
        assert {item.status for item in assignments} == {
            ReviewAssignmentStatus.IN_PROGRESS
        }
        assert {item.dossier_version_id for item in assignments} == {version.id}

        async with session_factory() as session:
            events = tuple((await session.scalars(select(OutboxEvent))).all())
            assert len(events) == 2
            payloads = {
                json.loads(
                    OutboxPayloadCipher(
                        key=OUTBOX_KEY,
                        key_id="test-review-key",
                    ).decrypt(
                        nonce=event.payload_nonce,
                        ciphertext=event.payload_ciphertext,
                        event_type=event.event_type,
                        aggregate_id=event.aggregate_id,
                    )
                )["recipient_user_id"]
                for event in events
            }
            assert payloads == {
                str(users["reviewer"].id),
                str(users["reviewer_two"].id),
            }
            audit_rows = tuple((await session.scalars(select(AuditLog))).all())
            assert len(audit_rows) == 1
            assert audit_rows[0].action == "review.assignments.created"
            assert audit_rows[0].actor_user_id == users["admin"].id
            assert audit_rows[0].resource_type == "dossier"
            assert audit_rows[0].resource_id == str(dossier.id)
            assert audit_rows[0].after_json == {"assignment_count": 2}

        with pytest.raises(ReviewConflictError):
            await service.assign_reviewers(
                _principal(users["admin"], "SUPER_ADMIN"),
                dossier.id,
                reviewer_user_ids=(users["reviewer"].id,),
                due_at=None,
            )

        async with session_factory() as session:
            assignment_count = await session.scalar(
                select(func.count()).select_from(ReviewAssignment)
            )
            event_count = await session.scalar(
                select(func.count()).select_from(OutboxEvent)
            )
            assert assignment_count == 2
            assert event_count == 2
            assert await session.scalar(select(func.count()).select_from(AuditLog)) == 1

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_assignment_and_outbox_roll_back_when_audit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, dossier, _ = await _setup()

        def fail_audit(**_: object) -> None:
            raise RuntimeError("audit storage unavailable")

        monkeypatch.setattr(service._audit_service, "record", fail_audit)
        with pytest.raises(RuntimeError, match="audit storage unavailable"):
            await service.assign_reviewers(
                _principal(users["admin"], "SUPER_ADMIN"),
                dossier.id,
                reviewer_user_ids=(users["reviewer"].id,),
                due_at=None,
            )

        async with session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(ReviewAssignment))
                == 0
            )
            assert (
                await session.scalar(select(func.count()).select_from(OutboxEvent)) == 0
            )
            assert await session.scalar(select(func.count()).select_from(AuditLog)) == 0

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_assignment_rejects_wrong_scope_owner_nonreviewer_and_invalid_input() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, dossier, _ = await _setup()
        admin = _principal(users["admin"], "SUPER_ADMIN")

        with pytest.raises(ReviewForbiddenError):
            await service.assign_reviewers(
                _principal(users["member"], "USER"),
                dossier.id,
                reviewer_user_ids=(users["reviewer"].id,),
                due_at=None,
            )
        with pytest.raises(ReviewValidationError):
            await service.assign_reviewers(
                admin,
                dossier.id,
                reviewer_user_ids=(users["owner"].id,),
                due_at=None,
            )
        with pytest.raises(ReviewValidationError):
            await service.assign_reviewers(
                admin,
                dossier.id,
                reviewer_user_ids=(users["member"].id,),
                due_at=None,
            )
        with pytest.raises(ReviewValidationError):
            await service.assign_reviewers(
                admin,
                dossier.id,
                reviewer_user_ids=(
                    users["reviewer"].id,
                    users["reviewer"].id,
                ),
                due_at=None,
            )
        with pytest.raises(ReviewValidationError):
            await service.assign_reviewers(
                admin,
                dossier.id,
                reviewer_user_ids=(users["reviewer"].id,),
                due_at=NOW - timedelta(seconds=1),
            )

        async with session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(ReviewAssignment))
                == 0
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
