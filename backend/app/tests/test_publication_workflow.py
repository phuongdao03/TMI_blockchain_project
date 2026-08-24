import asyncio
import base64
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import Certificate, CertificateStatus
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.errors import (
    PublicWorkFeaturedWindowError,
    PublicWorkForbiddenError,
    PublicWorkNotPublishableError,
    PublicWorkVersionConflictError,
)
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.publication_service import (
    PublicationAction,
    PublicationService,
    PublicationTransitionError,
    assert_transition,
)

NOW = datetime(2026, 7, 31, 8, tzinfo=UTC)


def _principal(user_id: UUID, *roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=uuid4(),
        email="admin@example.test",
        roles=roles,
    )


def _cipher() -> OutboxPayloadCipher:
    return OutboxPayloadCipher.from_base64(
        encoded_key=base64.b64encode(b"x" * 32).decode(),
        key_id="test-key",
    )


async def _seed(session: AsyncSession, *, thumbnail: bool = True) -> tuple[UUID, UUID]:
    owner_id = uuid4()
    category_id = uuid4()
    dossier_id = uuid4()
    certificate_id = uuid4()
    media_id = uuid4()
    work_id = uuid4()
    async with session.begin():
        session.add(
            User(
                id=owner_id,
                email="owner@example.test",
                password_hash="hash",
                status=UserStatus.ACTIVE,
            )
        )
        session.add(Category(id=category_id, code="ART", name="Art"))
        session.add(
            Dossier(
                id=dossier_id,
                code="DOS-1502",
                owner_user_id=owner_id,
                category_id=category_id,
                title="Approved work",
                summary="Approved public summary",
                _status=DossierStatus.CERTIFICATE_ISSUED,
            )
        )
        session.add(
            MediaAsset(
                id=media_id,
                owner_user_id=owner_id,
                cloudinary_public_id="catalog/thumbnail",
                resource_type="image",
                access_mode="authenticated",
                original_filename="thumbnail.jpg",
                mime_type="image/jpeg",
                bytes=1024,
                status=MediaStatus.ACTIVE,
            )
        )
        session.add(
            Certificate(
                id=certificate_id,
                certificate_number="TMI-2026-1502",
                dossier_id=dossier_id,
                current_version_no=1,
                status=CertificateStatus.ACTIVE,
                issued_at=NOW,
                public_token_hash="b" * 64,
                qr_payload="https://example.test/verify/1502",
            )
        )
        session.add(
            PublicWork(
                id=work_id,
                dossier_id=dossier_id,
                certificate_id=certificate_id,
                owner_user_id=owner_id,
                slug="approved-work",
                title="Approved work",
                short_description="Approved public summary",
                category_id=category_id,
                thumbnail_media_id=media_id if thumbnail else None,
            )
        )
    return work_id, owner_id


def _service(session: AsyncSession) -> PublicationService:
    return PublicationService(
        session=session,
        audit=AuditService(session),
        payload_cipher=_cipher(),
        clock=lambda: NOW,
    )


def test_transition_table_rejects_undefined_paths() -> None:
    assert_transition(PublicationStatus.DRAFT, PublicationAction.PUBLISH)
    assert_transition(PublicationStatus.SUSPENDED, PublicationAction.HIDE)
    with pytest.raises(PublicationTransitionError):
        assert_transition(PublicationStatus.ARCHIVED, PublicationAction.PUBLISH)


def test_publish_checklist_permission_version_and_reason(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'publication.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            work_id, owner_id = await _seed(session, thumbnail=False)
            service = _service(session)
            with pytest.raises(PublicWorkForbiddenError):
                await service.publish(
                    _principal(owner_id, "USER"),
                    work_id,
                    expected_version=1,
                    visibility=PublicWorkVisibility.PUBLIC,
                    request_id="request-forbidden",
                )
            with pytest.raises(PublicWorkNotPublishableError) as error:
                await service.publish(
                    _principal(owner_id, "SUPER_ADMIN"),
                    work_id,
                    expected_version=1,
                    visibility=PublicWorkVisibility.PUBLIC,
                    request_id="request-checklist",
                )
            assert error.value.details == {"reasons": ["thumbnail_not_ready"]}

            async with session.begin():
                work = await session.get(PublicWork, work_id)
                media_id = await session.scalar(select(MediaAsset.id))
                assert work is not None
                assert media_id is not None
                work.thumbnail_media_id = media_id

            published = await service.publish(
                _principal(owner_id, "SUPER_ADMIN"),
                work_id,
                expected_version=1,
                visibility=PublicWorkVisibility.PUBLIC,
                request_id="request-publish",
            )
            assert published.publication_status is PublicationStatus.PUBLISHED
            assert published.visibility is PublicWorkVisibility.PUBLIC
            assert published.published_at == NOW
            assert published.version == 2

            with pytest.raises(PublicWorkVersionConflictError):
                await service.hide(
                    _principal(owner_id, "SUPER_ADMIN"),
                    work_id,
                    expected_version=1,
                    request_id="request-stale",
                )
            with pytest.raises(ValueError, match="reason"):
                await service.suspend(
                    _principal(owner_id, "SUPER_ADMIN"),
                    work_id,
                    expected_version=2,
                    reason=" ",
                    request_id="request-no-reason",
                )
            suspended = await service.suspend(
                _principal(owner_id, "SUPER_ADMIN"),
                work_id,
                expected_version=2,
                reason="Active ownership dispute",
                request_id="request-suspend",
            )
            assert suspended.publication_status is PublicationStatus.SUSPENDED
            assert suspended.visibility is PublicWorkVisibility.PRIVATE
            assert await session.scalar(select(func.count()).select_from(AuditLog)) == 2
            event_count = await session.scalar(
                select(func.count()).select_from(OutboxEvent)
            )
            assert event_count == 2
        await engine.dispose()

    asyncio.run(exercise())


def test_featured_window_uses_utc_versioning_and_clears_on_suspend(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'featured.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            work_id, owner_id = await _seed(session)
            service = _service(session)
            admin = _principal(owner_id, "SUPER_ADMIN")
            with pytest.raises(PublicWorkNotPublishableError) as error:
                await service.feature(
                    admin,
                    work_id,
                    expected_version=1,
                    featured_at=NOW,
                    featured_until=NOW + timedelta(hours=2),
                    request_id="feature-private-draft",
                )
            assert error.value.details == {
                "reasons": ["featured_requires_published_public"]
            }
            await service.publish(
                admin,
                work_id,
                expected_version=1,
                visibility=PublicWorkVisibility.PUBLIC,
                request_id="publish-before-feature",
            )
            with pytest.raises(PublicWorkForbiddenError):
                await service.feature(
                    _principal(owner_id, "USER"),
                    work_id,
                    expected_version=2,
                    featured_at=NOW,
                    featured_until=NOW + timedelta(hours=2),
                    request_id="feature-forbidden",
                )
            with pytest.raises(PublicWorkFeaturedWindowError):
                await service.feature(
                    admin,
                    work_id,
                    expected_version=2,
                    featured_at=NOW.replace(tzinfo=None),
                    featured_until=NOW + timedelta(hours=2),
                    request_id="feature-naive",
                )
            vietnam = timezone(timedelta(hours=7))
            featured = await service.feature(
                admin,
                work_id,
                expected_version=2,
                featured_at=NOW.astimezone(vietnam),
                featured_until=(NOW + timedelta(hours=2)).astimezone(vietnam),
                request_id="feature",
            )
            assert featured.featured_at == NOW
            assert featured.featured_until == NOW + timedelta(hours=2)
            assert featured.version == 3
            with pytest.raises(PublicWorkVersionConflictError):
                await service.feature(
                    admin,
                    work_id,
                    expected_version=2,
                    featured_at=NOW,
                    featured_until=NOW + timedelta(hours=3),
                    request_id="feature-retry-stale",
                )
            unfeatured = await service.unfeature(
                admin,
                work_id,
                expected_version=3,
                request_id="unfeature",
            )
            assert unfeatured.featured_at is None
            assert unfeatured.featured_until is None
            await service.feature(
                admin,
                work_id,
                expected_version=4,
                featured_at=NOW,
                featured_until=NOW + timedelta(hours=2),
                request_id="feature-again",
            )
            suspended = await service.suspend(
                admin,
                work_id,
                expected_version=5,
                reason="Legal hold",
                request_id="suspend-featured",
            )
            assert suspended.featured_at is None
            assert suspended.featured_until is None
            audit_count = await session.scalar(
                select(func.count()).select_from(AuditLog)
            )
            assert audit_count == 5
        await engine.dispose()

    asyncio.run(exercise())


def test_scheduled_publication_is_idempotent(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'schedule.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            work_id, owner_id = await _seed(session)
            service = _service(session)
            scheduled_for = (NOW + timedelta(hours=1)).astimezone(
                timezone(timedelta(hours=7))
            )
            scheduled_for_utc = NOW + timedelta(hours=1)
            scheduled = await service.schedule(
                _principal(owner_id, "SUPER_ADMIN"),
                work_id,
                expected_version=1,
                visibility=PublicWorkVisibility.UNLISTED,
                publish_at=scheduled_for,
                request_id="request-schedule",
            )
            assert scheduled.publication_status is PublicationStatus.PENDING_PUBLICATION
            assert scheduled.scheduled_publish_at == scheduled_for_utc
            assert await service.publish_due(now=NOW, limit=10) == 0
            assert await service.publish_due(now=scheduled_for_utc, limit=10) == 1
            assert await service.publish_due(now=scheduled_for_utc, limit=10) == 0

            refreshed = await session.get(PublicWork, work_id)
            assert refreshed is not None
            assert refreshed.publication_status is PublicationStatus.PUBLISHED
            assert refreshed.visibility is PublicWorkVisibility.UNLISTED
            assert refreshed.version == 3
            assert await session.scalar(select(func.count()).select_from(AuditLog)) == 2
            event_count = await session.scalar(
                select(func.count()).select_from(OutboxEvent)
            )
            assert event_count == 2
        await engine.dispose()

    asyncio.run(exercise())


def test_concurrent_publish_allows_one_version_claim(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'concurrent.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as seed_session:
            work_id, owner_id = await _seed(seed_session)

        async with factory() as first_session, factory() as second_session:
            principal = _principal(owner_id, "SUPER_ADMIN")
            results = await asyncio.gather(
                _service(first_session).publish(
                    principal,
                    work_id,
                    expected_version=1,
                    visibility=PublicWorkVisibility.PUBLIC,
                    request_id="concurrent-first",
                ),
                _service(second_session).publish(
                    principal,
                    work_id,
                    expected_version=1,
                    visibility=PublicWorkVisibility.PUBLIC,
                    request_id="concurrent-second",
                ),
                return_exceptions=True,
            )
        assert sum(isinstance(result, PublicWork) for result in results) == 1
        assert (
            sum(
                isinstance(result, PublicWorkVersionConflictError) for result in results
            )
            == 1
        )
        async with factory() as verification_session:
            work = await verification_session.get(PublicWork, work_id)
            assert work is not None
            assert work.version == 2
            assert work.publication_status is PublicationStatus.PUBLISHED
            assert (
                await verification_session.scalar(
                    select(func.count()).select_from(OutboxEvent)
                )
                == 1
            )
        await engine.dispose()

    asyncio.run(exercise())
