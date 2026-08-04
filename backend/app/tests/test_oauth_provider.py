import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.errors import DomainError
from app.modules.auth.oauth import (
    OAuthAttempt,
    RedisOAuthRateLimiter,
    RedisOAuthStateStore,
    create_oauth_attempt,
    validate_oauth_next,
)
from app.modules.auth.oauth_provider import GoogleOIDCProvider

NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, tuple[bytes, int]] = {}
        self.now = 0

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = (value.encode(), self.now + ttl)

    async def eval(
        self,
        script: str,
        count: int,
        key: str,
        *arguments: int,
    ) -> bytes | list[int] | None:
        del count
        if arguments:
            current = int((self.values.get(key) or (b"0", 0))[0]) + 1
            self.values[key] = (str(current).encode(), self.now + arguments[0])
            return [current, arguments[0]]
        del script
        value = self.values.get(key)
        if value is None or value[1] <= self.now:
            self.values.pop(key, None)
            return None
        self.values.pop(key)
        return value[0]

    async def incr(self, key: str) -> int:
        value = int((self.values.get(key) or (b"0", 0))[0]) + 1
        self.values[key] = (str(value).encode(), self.now + 60)
        return value

    async def expire(self, key: str, ttl: int) -> bool:
        del ttl
        return key in self.values


class FakeHttpClient:
    def __init__(self) -> None:
        self.post_response = httpx.Response(200, json={"id_token": "token"})
        self.get_response = httpx.Response(200, json={"keys": []})
        self.post_error: Exception | None = None
        self.get_error: Exception | None = None

    async def post(
        self,
        url: str,
        *,
        data: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        del url, data, timeout
        if self.post_error is not None:
            raise self.post_error
        return self.post_response

    async def get(self, url: str, *, timeout: float) -> httpx.Response:
        del url, timeout
        if self.get_error is not None:
            raise self.get_error
        return self.get_response

    async def aclose(self) -> None:
        return None


class FailingRedis(FakeRedis):
    async def setex(self, key: str, ttl: int, value: str) -> None:
        del key, ttl, value
        raise OSError("redis unavailable")


def _provider(
    http_client: FakeHttpClient,
    *,
    clock: datetime = NOW,
) -> GoogleOIDCProvider:
    return GoogleOIDCProvider(
        client_id="google-client-id",
        client_secret="google-client-secret",
        redirect_uri="https://app.example.test/api/v1/auth/oauth/google/callback",
        authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        issuer="https://accounts.google.com",
        timeout_seconds=2,
        http_client=http_client,
        clock=lambda: clock,
    )


def _signed_token(
    private_key: Any,
    *,
    issuer: str = "https://accounts.google.com",
    audience: str = "google-client-id",
    nonce: str = "nonce-1",
    email_verified: bool = True,
    expires_at: datetime | None = None,
) -> str:
    expiration = expires_at or (NOW + timedelta(minutes=5))
    return jwt.encode(
        {
            "iss": issuer,
            "sub": "google-subject-1",
            "aud": audience,
            "iat": int(NOW.timestamp()),
            "exp": int(expiration.timestamp()),
            "nonce": nonce,
            "email": "viewer@gmail.com",
            "email_verified": email_verified,
            "name": "Viewer",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def _configure_jwks(client: FakeHttpClient, private_key: Any) -> None:
    public_jwk = json.loads(
        jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key())
    )
    public_jwk["kid"] = "test-key"
    client.get_response = httpx.Response(200, json={"keys": [public_jwk]})


def test_oauth_state_is_one_time_ttl_bound_and_safe_next_is_enforced() -> None:
    async def exercise() -> None:
        redis = FakeRedis()
        store = RedisOAuthStateStore(redis, ttl_seconds=300)  # type: ignore[arg-type]
        attempt = create_oauth_attempt(account_type="PUBLIC_USER", next_path="/account")
        await store.save(attempt)
        assert await store.consume(attempt.state) == attempt
        assert await store.consume(attempt.state) is None
        assert await store.consume("different-state") is None

        expired = create_oauth_attempt(account_type="PUBLIC_USER", next_path="/")
        await store.save(expired)
        redis.now = 301
        assert await store.consume(expired.state) is None

    asyncio.run(exercise())
    assert validate_oauth_next(None) == "/"
    assert validate_oauth_next("/workspace?tab=overview") == (
        "/workspace?tab=overview"
    )
    for unsafe in ("https://evil.example", "//evil.example", "workspace", "/\x00"):
        with pytest.raises(DomainError) as error:
            validate_oauth_next(unsafe)
        assert error.value.code == "OAUTH_STATE_INVALID"


def test_oauth_state_store_maps_redis_failure_to_safe_error() -> None:
    async def exercise() -> None:
        store = RedisOAuthStateStore(FailingRedis(), ttl_seconds=300)  # type: ignore[arg-type]
        with pytest.raises(DomainError) as error:
            await store.save(create_oauth_attempt("PUBLIC_USER", "/"))
        assert error.value.code == "OAUTH_PROVIDER_UNAVAILABLE"

    asyncio.run(exercise())


def test_google_authorization_url_does_not_include_client_secret() -> None:
    attempt = OAuthAttempt(
        state="state-1",
        nonce="nonce-1",
        account_type="PUBLIC_USER",
        next_path="/account",
    )
    url = _provider(FakeHttpClient()).authorization_url(attempt)
    assert "client_secret" not in url
    assert "state=state-1" in url
    assert "nonce=nonce-1" in url
    assert "redirect_uri=https%3A%2F%2Fapp.example.test" in url


def test_google_id_token_validates_signature_claims_nonce_and_email() -> None:
    async def exercise() -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        client = FakeHttpClient()
        _configure_jwks(client, private_key)
        provider = _provider(client)
        claims = await provider.validate_id_token(
            _signed_token(private_key), expected_nonce="nonce-1"
        )
        assert claims.subject == "google-subject-1"
        assert claims.email == "viewer@gmail.com"
        assert claims.email_verified is True

        with pytest.raises(DomainError) as nonce_error:
            await provider.validate_id_token(
                _signed_token(private_key, nonce="wrong"), expected_nonce="nonce-1"
            )
        assert nonce_error.value.code == "OAUTH_IDENTITY_INVALID"

        with pytest.raises(DomainError) as email_error:
            await provider.validate_id_token(
                _signed_token(private_key, email_verified=False),
                expected_nonce="nonce-1",
            )
        assert email_error.value.code == "OAUTH_IDENTITY_INVALID"

        with pytest.raises(DomainError) as issuer_error:
            await provider.validate_id_token(
                _signed_token(private_key, issuer="https://evil.example"),
                expected_nonce="nonce-1",
            )
        assert issuer_error.value.code == "OAUTH_IDENTITY_INVALID"

        with pytest.raises(DomainError) as audience_error:
            await provider.validate_id_token(
                _signed_token(private_key, audience="another-client"),
                expected_nonce="nonce-1",
            )
        assert audience_error.value.code == "OAUTH_IDENTITY_INVALID"

        with pytest.raises(DomainError) as expiry_error:
            await provider.validate_id_token(
                _signed_token(
                    private_key,
                    expires_at=NOW - timedelta(seconds=1),
                ),
                expected_nonce="nonce-1",
            )
        assert expiry_error.value.code == "OAUTH_IDENTITY_INVALID"

        another_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with pytest.raises(DomainError) as signature_error:
            await provider.validate_id_token(
                _signed_token(another_key), expected_nonce="nonce-1"
            )
        assert signature_error.value.code == "OAUTH_IDENTITY_INVALID"

    asyncio.run(exercise())


def test_google_code_exchange_maps_timeout_and_non_2xx_without_leaking_code() -> None:
    async def exercise() -> None:
        client = FakeHttpClient()
        provider = _provider(client)
        with pytest.raises(DomainError) as invalid_error:
            client.post_response = httpx.Response(400, json={"error": "invalid_grant"})
            await provider.exchange_code("secret-code")
        assert invalid_error.value.code == "OAUTH_CODE_INVALID"
        assert "secret-code" not in str(invalid_error.value)

        client.post_error = httpx.ReadTimeout("provider timeout")
        with pytest.raises(DomainError) as timeout_error:
            await provider.exchange_code("secret-code")
        assert timeout_error.value.code == "OAUTH_PROVIDER_UNAVAILABLE"
        assert "secret-code" not in str(timeout_error.value)

    asyncio.run(exercise())


def test_oauth_rate_limiter_hashes_ip_and_rejects_repeated_attempts() -> None:
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
