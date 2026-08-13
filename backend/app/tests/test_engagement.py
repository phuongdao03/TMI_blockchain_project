import asyncio
from datetime import date
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import DomainError
from app.main import create_application
from app.modules.engagement.errors import EngagementRateLimitedError
from app.modules.engagement.redis import RedisViewDeduplicator
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
    def __init__(self, *, work_id: UUID | None = WORK_ID) -> None:
        self.work_id = work_id
        self.increments: list[tuple[UUID, date]] = []

    async def find_published_public_work_id(self, _slug: str) -> UUID | None:
        return self.work_id

    async def increment_view(
        self,
        *,
        public_work_id: UUID,
        metric_date: date,
    ) -> bool:
        self.increments.append((public_work_id, metric_date))
        return True

    async def increment_share(
        self,
        *,
        public_work_id: UUID,
        metric_date: date,
    ) -> bool:
        del public_work_id, metric_date
        return True


class FakeDeduplicator:
    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted
        self.calls: list[tuple[str, str]] = []

    async def accept(self, *, visitor: str, public_work_id: str) -> bool:
        self.calls.append((visitor, public_work_id))
        return self.accepted


def test_view_service_only_increments_an_accepted_published_view() -> None:
    repository = FakeRepository()
    views = FakeDeduplicator(accepted=True)
    service = EngagementService(
        cast(AsyncSession, FakeSession()),
        repository=repository,
        views=views,
    )

    accepted = asyncio.run(service.record_view(slug="public-work", visitor="visitor"))

    assert accepted is True
    assert views.calls == [("visitor", str(WORK_ID))]
    assert len(repository.increments) == 1


def test_view_service_leaves_duplicate_and_unpublished_work_unchanged() -> None:
    duplicate_repository = FakeRepository()
    duplicate_service = EngagementService(
        cast(AsyncSession, FakeSession()),
        repository=duplicate_repository,
        views=FakeDeduplicator(accepted=False),
    )
    assert (
        asyncio.run(
            duplicate_service.record_view(slug="public-work", visitor="visitor")
        )
        is False
    )
    assert duplicate_repository.increments == []

    unpublished_service = EngagementService(
        cast(AsyncSession, FakeSession()),
        repository=FakeRepository(work_id=None),
        views=FakeDeduplicator(accepted=True),
    )
    with pytest.raises(DomainError) as captured:
        asyncio.run(
            unpublished_service.record_view(slug="private-work", visitor="visitor")
        )
    assert captured.value.code == "PUBLIC_WORK_NOT_FOUND"


class RedisFailure:
    async def set(self, *_args: object, **_kwargs: object) -> None:
        raise RedisError("unavailable")


def test_view_deduplicator_fails_closed_when_redis_is_unavailable() -> None:
    deduplicator = RedisViewDeduplicator(
        cast(Redis, RedisFailure()),
        visitor_context=EngagementVisitorContext(secret="s" * 32),
        ttl_seconds=86_400,
    )
    with pytest.raises(DomainError) as captured:
        asyncio.run(deduplicator.accept(visitor="visitor", public_work_id=str(WORK_ID)))
    assert captured.value.code == "ENGAGEMENT_UNAVAILABLE"


class StubEngagementService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def record_view(self, *, slug: str, visitor: str) -> bool:
        self.calls.append((slug, visitor))
        return True


def test_view_api_sets_only_a_signed_http_only_visitor_cookie() -> None:
    service = StubEngagementService()
    app = create_application(
        settings=Settings(
            engagement_visitor_hmac_secret=SecretStr("s" * 32),
        )
    )
    app.dependency_overrides[get_engagement_service] = lambda: service
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    app.dependency_overrides[enforce_public_engagement_rate_limit] = lambda: None
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/public/works/public-work/engagement/views")
            assert created.status_code == 204
            cookie = created.headers["set-cookie"]
            assert "tmi_engagement_visitor=" in cookie
            assert "HttpOnly" in cookie
            assert "SameSite=lax" in cookie

            repeated = client.post("/api/v1/public/works/public-work/engagement/views")
            assert repeated.status_code == 204
            assert "set-cookie" not in repeated.headers
    finally:
        app.dependency_overrides.clear()


def test_view_api_uses_the_engagement_rate_limit_contract() -> None:
    app = create_application(
        settings=Settings(
            engagement_visitor_hmac_secret=SecretStr("s" * 32),
        )
    )

    async def limited() -> None:
        raise EngagementRateLimitedError(retry_after_seconds=12)

    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    app.dependency_overrides[enforce_public_engagement_rate_limit] = limited
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/public/works/public-work/engagement/views")
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "ENGAGEMENT_RATE_LIMITED"
    finally:
        app.dependency_overrides.clear()
