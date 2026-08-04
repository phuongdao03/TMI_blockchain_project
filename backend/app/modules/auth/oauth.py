import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.parse import urlsplit

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.auth.errors import (
    OAuthProviderUnavailableError,
    OAuthRateLimitedError,
    OAuthStateInvalidError,
)
from app.modules.auth.models import AccountType

OAUTH_STATE_KEY_PREFIX = "auth:oauth:google:state:"
OAUTH_RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""
OAUTH_STATE_CONSUME_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if value then redis.call('DEL', KEYS[1]) end
return value
"""


@dataclass(frozen=True, slots=True)
class OAuthAttempt:
    state: str
    nonce: str
    account_type: str
    next_path: str
    purpose: str = "login"
    user_id: str | None = None


class OAuthStateStore(Protocol):
    async def save(self, attempt: OAuthAttempt) -> None: ...

    async def consume(self, state: str) -> OAuthAttempt | None: ...


class OAuthAttemptRateLimiter(Protocol):
    async def check(self, client_ip: str) -> None: ...


def validate_oauth_next(next_path: str | None) -> str:
    value = "/" if next_path is None else next_path
    if not isinstance(value, str) or len(value) > 512:
        raise OAuthStateInvalidError()
    if not value.startswith("/") or value.startswith("//"):
        raise OAuthStateInvalidError()
    if any(ord(character) < 0x20 for character in value) or "\\" in value:
        raise OAuthStateInvalidError()
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise OAuthStateInvalidError()
    return value


def resolve_oauth_next(next_path: str, roles: tuple[str, ...]) -> str:
    safe_next = validate_oauth_next(next_path)
    if safe_next not in {"/", "/dashboard"}:
        return safe_next
    role_set = set(roles)
    if "SUPER_ADMIN" in role_set or role_set & {
        "CONTENT_ADMIN",
        "FINANCE_ADMIN",
        "BLOCKCHAIN_ADMIN",
    }:
        return "/admin/dashboard"
    if role_set & {"COUNCIL_SECRETARY", "COUNCIL_MEMBER"}:
        return "/hoi-dong"
    if "REVIEWER" in role_set:
        return "/tham-dinh"
    return "/dashboard"


def create_oauth_attempt(
    account_type: str | AccountType,
    next_path: str | None,
    *,
    purpose: str = "login",
    user_id: str | None = None,
) -> OAuthAttempt:
    try:
        normalized_account_type = AccountType(account_type).value
    except ValueError as exc:
        raise OAuthStateInvalidError() from exc
    if purpose not in {"login", "link"} or (
        (purpose == "link") != (user_id is not None)
    ):
        raise OAuthStateInvalidError()
    return OAuthAttempt(
        state=secrets.token_urlsafe(32),
        nonce=secrets.token_urlsafe(32),
        account_type=normalized_account_type,
        next_path=validate_oauth_next(next_path),
        purpose=purpose,
        user_id=user_id,
    )


class RedisOAuthStateStore:
    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def save(self, attempt: OAuthAttempt) -> None:
        payload = json.dumps(
            {
                "state": attempt.state,
                "nonce": attempt.nonce,
                "account_type": attempt.account_type,
                "next_path": attempt.next_path,
                "purpose": attempt.purpose,
                "user_id": attempt.user_id,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        try:
            await self._redis.setex(
                self._key(attempt.state),
                self._ttl_seconds,
                payload,
            )
        except (RedisError, OSError, TimeoutError) as exc:
            raise OAuthProviderUnavailableError() from exc

    async def consume(self, state: str) -> OAuthAttempt | None:
        if not state or len(state) > 512:
            return None
        try:
            raw = await self._redis.eval(
                OAUTH_STATE_CONSUME_SCRIPT,
                1,
                self._key(state),
            )
        except (RedisError, OSError, TimeoutError) as exc:
            raise OAuthProviderUnavailableError() from exc
        if raw is None:
            return None
        try:
            payload = json.loads(raw.decode() if isinstance(raw, bytes) else str(raw))
            if not isinstance(payload, dict):
                return None
            attempt = OAuthAttempt(
                state=str(payload["state"]),
                nonce=str(payload["nonce"]),
                account_type=AccountType(str(payload["account_type"])).value,
                next_path=validate_oauth_next(str(payload["next_path"])),
                purpose=str(payload.get("purpose", "login")),
                user_id=(
                    str(payload["user_id"])
                    if payload.get("user_id") is not None
                    else None
                ),
            )
            if attempt.purpose not in {"login", "link"}:
                return None
            return attempt if attempt.state == state else None
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _key(state: str) -> str:
        digest = hashlib.sha256(state.encode()).hexdigest()
        return f"{OAUTH_STATE_KEY_PREFIX}{digest}"


class RedisOAuthRateLimiter:
    def __init__(
        self,
        redis: Redis,
        *,
        attempts: int,
        window_seconds: int,
    ) -> None:
        self._redis = redis
        self._attempts = attempts
        self._window_seconds = window_seconds

    async def check(self, client_ip: str) -> None:
        digest = hashlib.sha256(client_ip.encode()).hexdigest()
        key = f"auth:oauth:rate:{digest}"
        try:
            result = await self._redis.eval(
                OAUTH_RATE_LIMIT_SCRIPT,
                1,
                key,
                self._window_seconds,
            )
        except (RedisError, OSError, TimeoutError) as exc:
            raise OAuthProviderUnavailableError() from exc
        count, retry_after = cast(list[int], result)
        if count > self._attempts:
            raise OAuthRateLimitedError(retry_after_seconds=max(retry_after, 1))
