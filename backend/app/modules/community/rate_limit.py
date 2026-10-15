from redis.asyncio import Redis

from app.core.config import Settings
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    SettingsDependency,
)
from app.modules.auth.errors import RateLimitExceededError, RateLimitUnavailableError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.errors import (
    CommunityRateLimitedError,
    CommunityRateLimitUnavailableError,
)
from app.modules.public.rate_limit import RedisPublicRateLimiter


async def _check_community_limit(
    principal: AuthPrincipal,
    settings: Settings,
    *,
    attempts: int,
    window_seconds: int,
    scope: str,
) -> None:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        limiter = RedisPublicRateLimiter(
            redis_client,
            attempts=attempts,
            window_seconds=window_seconds,
            scope=scope,
        )
        try:
            await limiter.check(str(principal.user_id))
        except RateLimitExceededError as exc:
            retry_after = exc.details.get("retry_after_seconds", 1)
            if not isinstance(retry_after, int):
                retry_after = 1
            raise CommunityRateLimitedError(
                retry_after_seconds=retry_after,
            ) from exc
        except RateLimitUnavailableError as exc:
            raise CommunityRateLimitUnavailableError() from exc
    finally:
        await redis_client.aclose()


async def enforce_community_content_write_rate_limit(
    principal: CsrfProtectedPrincipalDependency,
    settings: SettingsDependency,
) -> None:
    await _check_community_limit(
        principal,
        settings,
        attempts=settings.community_write_rate_limit,
        window_seconds=settings.community_write_rate_window_seconds,
        scope="community:write:content",
    )


async def enforce_community_engagement_write_rate_limit(
    principal: CsrfProtectedPrincipalDependency,
    settings: SettingsDependency,
) -> None:
    await _check_community_limit(
        principal,
        settings,
        attempts=settings.community_engagement_write_rate_limit,
        window_seconds=settings.community_engagement_write_rate_window_seconds,
        scope="community:write:engagement",
    )


async def enforce_community_report_write_rate_limit(
    principal: CsrfProtectedPrincipalDependency,
    settings: SettingsDependency,
) -> None:
    await _check_community_limit(
        principal,
        settings,
        attempts=settings.community_report_write_rate_limit,
        window_seconds=settings.community_report_write_rate_window_seconds,
        scope="community:write:report",
    )
