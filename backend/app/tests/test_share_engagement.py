import asyncio
from datetime import date
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_application
from app.modules.auth.dependencies import get_optional_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.engagement.errors import EngagementRateLimitedError
from app.modules.engagement.redis import RedisShareDeduplicator
from app.modules.engagement.service import EngagementService
from app.modules.engagement.visitor import EngagementVisitorContext
from app.modules.public.dependencies import (
    enforce_public_engagement_rate_limit,
    enforce_public_rate_limit,
    get_engagement_service,
)

WORK_ID = UUID("50000000-0000-0000-0000-000000000001")


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class FakeRepository:
    def __init__(self, work_id: UUID | None = WORK_ID) -> None:
        self.work_id = work_id
        self.shares: list[tuple[UUID, date]] = []

    async def find_published_public_work_id(self, _slug: str) -> UUID | None:
        return self.work_id

    async def increment_view(self, **_kwargs: object) -> bool:
        return True

    async def increment_share(
        self,
        *,
        public_work_id: UUID,
        metric_date: date,
    ) -> bool:
        self.shares.append((public_work_id, metric_date))
        return True


class FakeShares:
    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted
        self.calls: list[tuple[str, str, str]] = []

    async def accept(
        self,
        *,
        visitor: str,
        public_work_id: str,
        channel: str,
    ) -> bool:
        self.calls.append((visitor, public_work_id, channel))
        return self.accepted


class FakeViews:
    async def accept(self, *, visitor: str, public_work_id: str) -> bool:
        del visitor, public_work_id
        return True


class FakeActivity:
    def __init__(self) -> None:
        self.events: list[tuple[UUID, UUID, str]] = []

    async def record_share(
        self,
        *,
        user_id: UUID,
        public_work_id: UUID,
        channel: str,
    ) -> None:
        self.events.append((user_id, public_work_id, channel))


def test_share_service_counts_once_per_accepted_channel_intent() -> None:
    repository = FakeRepository()
    shares = FakeShares(accepted=True)
    service = EngagementService(
        cast(AsyncSession, FakeSession()),
        repository=repository,
        views=FakeViews(),
        shares=shares,
    )

    assert (
        asyncio.run(
            service.record_share(
                slug="public-work",
                visitor="visitor",
                channel="NATIVE",
            )
        )
        is True
    )
    assert shares.calls == [("visitor", str(WORK_ID), "NATIVE")]
    assert len(repository.shares) == 1


def test_anonymous_share_does_not_create_private_activity() -> None:
    activity = FakeActivity()
    service = EngagementService(
        cast(AsyncSession, FakeSession()),
        repository=FakeRepository(),
        views=FakeViews(),
        shares=FakeShares(True),
        activity=activity,
    )

    assert (
        asyncio.run(
            service.record_share(
                slug="public-work",
                visitor="visitor",
                channel="NATIVE",
            )
        )
        is True
    )
    assert activity.events == []


def test_authenticated_share_creates_private_activity_for_that_user() -> None:
    activity = FakeActivity()
    user_id = UUID("50000000-0000-0000-0000-000000000099")
    service = EngagementService(
        cast(AsyncSession, FakeSession()),
        repository=FakeRepository(),
        views=FakeViews(),
        shares=FakeShares(True),
        activity=activity,
    )

    assert asyncio.run(
        service.record_share(
            slug="public-work",
            visitor="visitor",
            channel="COPY_LINK",
            principal=AuthPrincipal(
                user_id=user_id,
                session_id=uuid4(),
                email="member@example.test",
                roles=("MEMBER",),
            ),
        )
    )
    assert activity.events == [(user_id, WORK_ID, "COPY_LINK")]


def test_share_service_hides_inaccessible_work_and_skips_duplicates() -> None:
    duplicate_repository = FakeRepository()
    duplicate_service = EngagementService(
        cast(AsyncSession, FakeSession()),
        repository=duplicate_repository,
        views=FakeViews(),
        shares=FakeShares(False),
    )
    assert (
        asyncio.run(
            duplicate_service.record_share(
                slug="public-work",
                visitor="visitor",
                channel="COPY_LINK",
            )
        )
        is False
    )
    assert duplicate_repository.shares == []

    missing_service = EngagementService(
        cast(AsyncSession, FakeSession()),
        repository=FakeRepository(work_id=None),
        views=FakeViews(),
        shares=FakeShares(True),
    )
    with pytest.raises(DomainError) as captured:
        asyncio.run(
            missing_service.record_share(
                slug="private-work",
                visitor="visitor",
                channel="NATIVE",
            )
        )
    assert captured.value.code == "PUBLIC_WORK_NOT_FOUND"


class FailingRedis:
    async def set(self, *_args: object, **_kwargs: object) -> None:
        raise RedisError("unavailable")


def test_share_deduplicator_uses_hashed_visitor_and_fails_closed() -> None:
    deduplicator = RedisShareDeduplicator(
        cast(Redis, FailingRedis()),
        visitor_context=EngagementVisitorContext(secret="s" * 32),
        ttl_seconds=86_400,
    )
    with pytest.raises(DomainError) as captured:
        asyncio.run(
            deduplicator.accept(
                visitor="visitor",
                public_work_id=str(WORK_ID),
                channel="NATIVE",
            )
        )
    assert captured.value.code == "ENGAGEMENT_UNAVAILABLE"


class StubEngagementService:
    async def record_share(self, **_kwargs: object) -> bool:
        return True


def test_share_api_validates_channel_and_returns_accepted_envelope() -> None:
    app = create_application(
        settings=Settings(engagement_visitor_hmac_secret=SecretStr("s" * 32))
    )
    app.dependency_overrides[get_engagement_service] = StubEngagementService
    app.dependency_overrides[get_optional_current_principal] = lambda: None
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    app.dependency_overrides[enforce_public_engagement_rate_limit] = lambda: None
    try:
        with TestClient(app) as client:
            accepted = client.post(
                "/api/v1/public/works/public-work/engagement/shares",
                json={"channel": "NATIVE"},
            )
            assert accepted.status_code == 202
            assert accepted.json()["data"] == {"accepted": True}
            assert "HttpOnly" in accepted.headers["set-cookie"]

            invalid = client.post(
                "/api/v1/public/works/public-work/engagement/shares",
                json={"channel": "EMAIL"},
            )
            assert invalid.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_share_api_uses_engagement_rate_limit_error() -> None:
    app = create_application(
        settings=Settings(engagement_visitor_hmac_secret=SecretStr("s" * 32))
    )

    async def limited() -> None:
        raise EngagementRateLimitedError(retry_after_seconds=12)

    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    app.dependency_overrides[enforce_public_engagement_rate_limit] = limited
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/public/works/public-work/engagement/shares",
                json={"channel": "NATIVE"},
            )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "ENGAGEMENT_RATE_LIMITED"
    finally:
        app.dependency_overrides.clear()
