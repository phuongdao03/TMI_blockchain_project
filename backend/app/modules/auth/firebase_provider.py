import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.modules.auth.errors import (
    OAuthIdentityInvalidError,
    OAuthProviderUnavailableError,
)

EMAIL_ADAPTER = TypeAdapter(EmailStr)
ALLOWED_SIGN_IN_PROVIDERS = frozenset({"google.com", "password"})


class FirebaseHttpClient(Protocol):
    async def get(self, url: str, *, timeout: float) -> httpx.Response: ...

    async def aclose(self) -> None: ...


@dataclass(frozen=True, slots=True)
class FirebaseClaims:
    subject: str
    email: str
    email_verified: bool
    name: str | None
    picture: str | None
    auth_time: datetime | None = None
    sign_in_second_factor: str | None = None
    second_factor_identifier: str | None = None

    @property
    def mfa_verified_at(self) -> datetime | None:
        if self.sign_in_second_factor != "totp":
            return None
        return self.auth_time


@dataclass(frozen=True, slots=True)
class FirebaseTokenVerifier:
    project_id: str
    jwks_uri: str
    timeout_seconds: float
    http_client: FirebaseHttpClient
    clock: Callable[[], datetime]
    emulator_host: str | None = None

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        jwks_uri: str,
        timeout_seconds: float,
        http_client: FirebaseHttpClient | None = None,
        clock: Callable[[], datetime] | None = None,
        emulator_host: str | None = None,
    ) -> "FirebaseTokenVerifier":
        return cls(
            project_id=project_id,
            jwks_uri=jwks_uri,
            timeout_seconds=timeout_seconds,
            http_client=http_client or httpx.AsyncClient(),
            clock=clock or (lambda: datetime.now(UTC)),
            emulator_host=emulator_host,
        )

    async def validate_id_token(self, id_token: str) -> FirebaseClaims:
        try:
            header = jwt.get_unverified_header(id_token)
            if self.emulator_host:
                if header.get("alg") != "none":
                    raise ValueError
                claims = jwt.decode(
                    id_token,
                    algorithms=["none"],
                    options={
                        "verify_signature": False,
                        "verify_aud": False,
                        "verify_iss": False,
                        "verify_exp": False,
                        "verify_iat": False,
                    },
                )
            else:
                if header.get("alg") != "RS256" or not isinstance(
                    header.get("kid"), str
                ):
                    raise ValueError
                certificate = await self._get_certificate(header["kid"])
                public_key = serialization.load_pem_public_key(certificate.encode())
                if not isinstance(public_key, RSAPublicKey):
                    raise ValueError
                claims = jwt.decode(
                    id_token,
                    public_key,
                    algorithms=["RS256"],
                    audience=self.project_id,
                    issuer=f"https://securetoken.google.com/{self.project_id}",
                    options={"verify_exp": False, "verify_iat": False},
                )
            if not isinstance(claims, Mapping):
                raise ValueError
            required_claims = {
                "iss",
                "sub",
                "aud",
                "iat",
                "exp",
                "auth_time",
                "email",
                "email_verified",
                "firebase",
            }
            if not required_claims.issubset(claims):
                raise ValueError
            if claims.get("iss") != f"https://securetoken.google.com/{self.project_id}":
                raise ValueError
            if claims.get("aud") != self.project_id:
                raise ValueError
            now = self.clock().timestamp()
            exp = claims.get("exp")
            issued_at = claims.get("iat")
            auth_time = claims.get("auth_time")
            if (
                not isinstance(exp, (int, float))
                or exp <= now
                or not isinstance(issued_at, (int, float))
                or issued_at > now + 60
                or not isinstance(auth_time, (int, float))
                or auth_time > now + 60
            ):
                raise ValueError
            firebase_claim = claims.get("firebase")
            if not isinstance(firebase_claim, Mapping):
                raise ValueError
            if firebase_claim.get("sign_in_provider") not in ALLOWED_SIGN_IN_PROVIDERS:
                raise ValueError
            email_verified = claims.get("email_verified") is True
            if not email_verified and not self.emulator_host:
                raise ValueError
            subject = claims.get("sub")
            email = claims.get("email")
            if not isinstance(subject, str) or not subject or len(subject) > 255:
                raise ValueError
            if not isinstance(email, str) or not email or len(email) > 320:
                raise ValueError
            normalized_email = str(EMAIL_ADAPTER.validate_python(email)).lower()
            return FirebaseClaims(
                subject=subject,
                email=normalized_email,
                email_verified=email_verified,
                name=_optional_string(claims.get("name")),
                picture=_optional_string(claims.get("picture")),
                auth_time=datetime.fromtimestamp(float(auth_time), tz=UTC),
                sign_in_second_factor=_optional_string(
                    firebase_claim.get("sign_in_second_factor")
                ),
                second_factor_identifier=_optional_string(
                    firebase_claim.get("second_factor_identifier")
                ),
            )
        except (jwt.InvalidTokenError, TypeError, ValueError, ValidationError) as exc:
            raise OAuthIdentityInvalidError() from exc

    async def _get_certificate(self, kid: str) -> str:
        try:
            response = await self.http_client.get(
                self.jwks_uri,
                timeout=self.timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise OAuthProviderUnavailableError() from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise OAuthProviderUnavailableError()
        try:
            payload = response.json()
            certificate = payload[kid]
            if not isinstance(certificate, str):
                raise ValueError
            return certificate
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise OAuthProviderUnavailableError() from None

    async def close(self) -> None:
        await self.http_client.aclose()


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


__all__ = ["FirebaseClaims", "FirebaseTokenVerifier"]
