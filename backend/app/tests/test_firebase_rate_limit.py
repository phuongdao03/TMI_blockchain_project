import asyncio

import pytest

from app.core.errors import DomainError
from app.modules.auth.oauth import RedisOAuthRateLimiter


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    async def eval(
        self,
        script: str,
        count: int,
        key: str,
        window_seconds: int,
    ) -> list[int]:
        del script, count
        value = self.values.get(key, 0) + 1
        self.values[key] = value
        return [value, window_seconds]


def test_firebase_rate_limiter_hashes_ip_and_rejects_repeated_attempts() -> None:
    async def exercise() -> None:
        redis = FakeRedis()
        limiter = RedisOAuthRateLimiter(
            redis,  # type: ignore[arg-type]
            attempts=1,
            window_seconds=60,
        )
        await limiter.check("203.0.113.7")
        with pytest.raises(DomainError) as error:
            await limiter.check("203.0.113.7")
        assert error.value.code == "OAUTH_RATE_LIMITED"
        assert all("203.0.113.7" not in key for key in redis.values)

    asyncio.run(exercise())
