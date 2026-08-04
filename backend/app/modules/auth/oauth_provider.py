import hmac
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast
from urllib.parse import urlencode

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.modules.auth.errors import (
    OAuthCodeInvalidError,
    OAuthIdentityInvalidError,
    OAuthProviderUnavailableError,
)
from app.modules.auth.oauth import OAuthAttempt

GOOGLE_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
EMAIL_ADAPTER = TypeAdapter(EmailStr)


class OAuthHttpClient(Protocol):
    async def post(
        self,
        url: str,
        *,
        data: dict[str, str],
        timeout: float,
    ) -> httpx.Response: ...

    async def get(self, url: str, *, timeout: float) -> httpx.Response: ...

    async def aclose(self) -> None: ...


@dataclass(frozen=True, slots=True)
class GoogleOIDCClaims:
    subject: str
    email: str
    email_verified: bool
    name: str | None
    picture: str | None


class GoogleOIDCProvider:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_endpoint: str,
        token_endpoint: str,
        jwks_uri: str,
        issuer: str,
        timeout_seconds: float,
        http_client: OAuthHttpClient | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._authorization_endpoint = authorization_endpoint
        self._token_endpoint = token_endpoint
        self._jwks_uri = jwks_uri
        self._issuers = GOOGLE_ISSUERS | {issuer}
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client or httpx.AsyncClient()
        self._owns_http_client = http_client is None
        self._clock = clock or (lambda: datetime.now(UTC))

    def authorization_url(self, attempt: OAuthAttempt) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": attempt.state,
                "nonce": attempt.nonce,
                "prompt": "select_account",
            }
        )
        return f"{self._authorization_endpoint}?{query}"

    async def exchange_code(self, code: str) -> str:
        if not code or len(code) > 4_096:
            raise OAuthCodeInvalidError()
        try:
            response = await self._http_client.post(
                self._token_endpoint,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=self._timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise OAuthProviderUnavailableError() from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise OAuthCodeInvalidError()
        try:
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise ValueError
            id_token = payload.get("id_token")
            if not isinstance(id_token, str) or not id_token:
                raise ValueError
            return id_token
        except (ValueError, TypeError):
            raise OAuthCodeInvalidError() from None

    async def validate_id_token(
        self,
        id_token: str,
        *,
        expected_nonce: str,
    ) -> GoogleOIDCClaims:
        try:
            header = jwt.get_unverified_header(id_token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                raise ValueError
            jwk = await self._get_signing_key(header["kid"])
            key = cast(
                RSAPublicKey,
                jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk)),
            )
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=self._issuers,
                options={
                    "require": [
                        "iss",
                        "sub",
                        "aud",
                        "iat",
                        "exp",
                        "nonce",
                        "email",
                        "email_verified",
                    ],
                    "verify_exp": False,
                },
            )
            if not isinstance(claims, Mapping):
                raise ValueError
            exp = claims.get("exp")
            now = self._clock()
            if not isinstance(exp, (int, float)) or exp <= now.timestamp():
                raise ValueError
            nonce = claims.get("nonce")
            if not isinstance(nonce, str) or not hmac.compare_digest(
                nonce, expected_nonce
            ):
                raise ValueError
            if claims.get("email_verified") is not True:
                raise ValueError
            subject = claims.get("sub")
            if not isinstance(subject, str) or not subject or len(subject) > 255:
                raise ValueError
            email_value = claims.get("email")
            if not isinstance(email_value, str):
                raise ValueError
            email = str(EMAIL_ADAPTER.validate_python(email_value)).lower()
            audience = claims.get("aud")
            if isinstance(audience, list) and len(audience) > 1:
                if claims.get("azp") != self._client_id:
                    raise ValueError
            return GoogleOIDCClaims(
                subject=subject,
                email=email,
                email_verified=True,
                name=_optional_claim(claims.get("name")),
                picture=_optional_claim(claims.get("picture")),
            )
        except (
            jwt.InvalidTokenError,
            KeyError,
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            raise OAuthIdentityInvalidError() from exc

    async def _get_signing_key(self, kid: str) -> Mapping[str, object]:
        try:
            response = await self._http_client.get(
                self._jwks_uri,
                timeout=self._timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise OAuthProviderUnavailableError() from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise OAuthProviderUnavailableError()
        try:
            payload = response.json()
            keys = payload["keys"]
            if not isinstance(keys, list):
                raise ValueError
            for candidate in keys:
                if isinstance(candidate, Mapping) and candidate.get("kid") == kid:
                    return candidate
        except (KeyError, TypeError, ValueError):
            raise OAuthProviderUnavailableError() from None
        raise OAuthIdentityInvalidError()

    async def close(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()


def _optional_claim(value: object) -> str | None:
    return value if isinstance(value, str) else None
