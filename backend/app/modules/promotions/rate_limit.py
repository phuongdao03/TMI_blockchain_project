from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.errors import DomainError
from app.modules.auth.dependencies import CurrentPrincipalDependency, SettingsDependency


async def enforce_promotion_rate_limit(
    request: Request,
    principal: CurrentPrincipalDependency,
    settings: SettingsDependency,
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"} or settings.app_env == "local":
        return
    limit = 20 if "promotion-media" in request.url.path else 120
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        count = int(
            await client.eval(
                (
                    "local n=redis.call('INCR',KEYS[1]); "
                    "if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n"
                ),
                1,
                f"promotion-writes:{principal.user_id}",
            )
        )
    except RedisError as error:
        raise DomainError(
            code="PROMOTION_RATE_LIMIT_UNAVAILABLE",
            message="Chưa thể xác minh giới hạn yêu cầu. Vui lòng thử lại.",
            status_code=503,
        ) from error
    finally:
        await client.aclose()
    if count > limit:
        raise DomainError(
            code="PROMOTION_RATE_LIMIT",
            message="Bạn thao tác quá nhanh. Vui lòng thử lại sau một phút.",
            status_code=429,
        )
