import asyncio
import hashlib
from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute
from redis.exceptions import RedisError

from app.core.config import Settings
from app.modules.auth.session_service import AuthPrincipal
from app.modules.community import rate_limit
from app.modules.community.errors import (
    CommunityRateLimitedError,
    CommunityRateLimitUnavailableError,
)


def test_community_post_image_limits_are_configurable_with_bounded_values() -> None:
    settings = Settings(
        _env_file=None,
        community_post_image_max_bytes=8_388_608,
        community_post_image_max_count=8,
    )

    assert settings.community_post_image_max_bytes == 8_388_608
    assert settings.community_post_image_max_count == 8
    with pytest.raises(ValueError):
        Settings(_env_file=None, community_post_image_max_count=11)
    with pytest.raises(ValueError):
        Settings(_env_file=None, community_post_image_max_bytes=20_971_521)


class _FakeRedis:
    def __init__(self, count: int = 1, *, failure: Exception | None = None) -> None:
        self.count = count
        self.failure = failure
        self.eval_args: tuple[object, ...] | None = None
        self.closed = False

    async def eval(self, *args: object) -> list[int]:
        self.eval_args = args
        if self.failure is not None:
            raise self.failure
        return [self.count, 42]

    async def aclose(self) -> None:
        self.closed = True


def _principal(user_id: UUID | None = None) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id or uuid4(),
        session_id=uuid4(),
        email="private@example.test",
        roles=("USER",),
    )


@pytest.mark.parametrize(
    ("dependency", "scope", "attempts_field", "window_field"),
    [
        (
            rate_limit.enforce_community_content_write_rate_limit,
            "community:write:content",
            "community_write_rate_limit",
            "community_write_rate_window_seconds",
        ),
        (
            rate_limit.enforce_community_engagement_write_rate_limit,
            "community:write:engagement",
            "community_engagement_write_rate_limit",
            "community_engagement_write_rate_window_seconds",
        ),
        (
            rate_limit.enforce_community_report_write_rate_limit,
            "community:write:report",
            "community_report_write_rate_limit",
            "community_report_write_rate_window_seconds",
        ),
    ],
)
def test_community_write_limits_hash_user_key_and_use_configured_bucket(
    monkeypatch: pytest.MonkeyPatch,
    dependency: Callable[..., object],
    scope: str,
    attempts_field: str,
    window_field: str,
) -> None:
    principal = _principal(UUID("b0000000-0000-0000-0000-000000000001"))
    settings = Settings(
        _env_file=None,
        **{attempts_field: 3, window_field: 77},
    )
    fake = _FakeRedis(count=3)
    monkeypatch.setattr(rate_limit.Redis, "from_url", lambda _url: fake)

    asyncio.run(dependency(principal, settings))

    assert fake.eval_args is not None
    assert fake.eval_args[1] == 1
    assert fake.eval_args[2] == (
        f"{scope}:{hashlib.sha256(str(principal.user_id).encode()).hexdigest()}"
    )
    assert fake.eval_args[3] == 77
    assert fake.closed is True


def test_community_write_limit_returns_429_when_bucket_is_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = _principal()
    settings = Settings(_env_file=None, community_write_rate_limit=2)
    fake = _FakeRedis(count=3)
    monkeypatch.setattr(rate_limit.Redis, "from_url", lambda _url: fake)

    with pytest.raises(CommunityRateLimitedError) as error:
        asyncio.run(
            rate_limit.enforce_community_content_write_rate_limit(
                principal,
                settings,
            )
        )

    assert error.value.status_code == 429
    assert error.value.details == {"retry_after_seconds": 42}
    assert fake.closed is True


def test_community_write_limit_fails_closed_when_redis_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = _principal()
    settings = Settings(_env_file=None)
    fake = _FakeRedis(failure=RedisError("offline"))
    monkeypatch.setattr(rate_limit.Redis, "from_url", lambda _url: fake)

    with pytest.raises(CommunityRateLimitUnavailableError) as error:
        asyncio.run(
            rate_limit.enforce_community_content_write_rate_limit(
                principal,
                settings,
            )
        )

    assert error.value.status_code == 503
    assert fake.closed is True


def _direct_dependency_calls(route: APIRoute) -> set[object]:
    return {dependency.call for dependency in route.dependant.dependencies}


def test_all_community_mutation_routes_have_the_expected_rate_bucket() -> None:
    from app.api.v1 import community, community_admin, community_engagement

    routes = [
        route
        for router in (
            community.router,
            community.moderation_router,
            community_engagement.router,
            community_admin.router,
            community_admin.admin_router,
        )
        for route in router.routes
        if isinstance(route, APIRoute)
    ]
    route_calls = {
        (route.path, method): _direct_dependency_calls(route)
        for route in routes
        for method in route.methods or ()
    }
    content = rate_limit.enforce_community_content_write_rate_limit
    engagement = rate_limit.enforce_community_engagement_write_rate_limit
    reports = rate_limit.enforce_community_report_write_rate_limit

    expected_content = {
        ("/api/v1/community/posts", "POST"),
        ("/api/v1/community/posts/{post_id}/submit", "POST"),
        ("/api/v1/community/posts/{post_id}", "PATCH"),
        ("/api/v1/community/posts/{post_id}", "DELETE"),
        ("/api/v1/community/posts/{post_id}/comments", "POST"),
        ("/api/v1/community/comments/{comment_id}", "PATCH"),
        ("/api/v1/community/comments/{comment_id}", "DELETE"),
        ("/api/v1/admin/community/reports/{report_id}/resolve", "POST"),
        ("/api/v1/admin/community/posts/{post_id}/hide", "POST"),
        ("/api/v1/admin/community/posts/{post_id}/restore", "POST"),
        ("/api/v1/admin/community/comments/{comment_id}/hide", "POST"),
        ("/api/v1/admin/community/comments/{comment_id}/restore", "POST"),
        ("/api/v1/admin/community/categories", "POST"),
        ("/api/v1/admin/community/categories/{category_id}", "PATCH"),
    }
    expected_engagement = {
        ("/api/v1/community/posts/{post_id}/like", "PUT"),
        ("/api/v1/community/posts/{post_id}/like", "DELETE"),
        ("/api/v1/community/posts/{post_id}/bookmark", "PUT"),
        ("/api/v1/community/posts/{post_id}/bookmark", "DELETE"),
        ("/api/v1/community/members/{member_id}/follow", "PUT"),
        ("/api/v1/community/members/{member_id}/follow", "DELETE"),
    }
    expected_reports = {
        ("/api/v1/community/posts/{post_id}/reports", "POST"),
        ("/api/v1/community/comments/{comment_id}/reports", "POST"),
    }

    assert all(content in route_calls[route] for route in expected_content)
    assert all(engagement in route_calls[route] for route in expected_engagement)
    assert all(reports in route_calls[route] for route in expected_reports)
    assert not {
        content,
        engagement,
        reports,
    }.intersection(route_calls[("/api/v1/community/posts", "GET")])
