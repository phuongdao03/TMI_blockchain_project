import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.modules.auth.errors import OAuthIdentityInvalidError
from app.modules.auth.firebase_provider import FirebaseTokenVerifier


class FakeFirebaseClient:
    def __init__(self, certificate: str) -> None:
        self.certificate = certificate

    async def get(self, url: str, *, timeout: float) -> httpx.Response:
        del url, timeout
        return httpx.Response(200, json={"firebase-key": self.certificate})

    async def aclose(self) -> None:
        return None


@pytest.mark.parametrize("sign_in_provider", ["google.com", "password"])
def test_firebase_token_is_verified_and_normalized(
    sign_in_provider: str,
) -> None:
    key = rsa.generate_private_key(public_exponent=65_537, key_size=2_048)
    public_key = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    now = datetime(2026, 8, 6, 8, tzinfo=UTC)
    token = jwt.encode(
        {
            "iss": "https://securetoken.google.com/tmi-test",
            "aud": "tmi-test",
            "sub": "firebase-user-1",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "auth_time": int(now.timestamp()),
            "email": "Owner@Example.com",
            "email_verified": True,
            "name": "Owner",
            "firebase": {"sign_in_provider": sign_in_provider},
        },
        key,
        algorithm="RS256",
        headers={"kid": "firebase-key"},
    )
    verifier = FirebaseTokenVerifier.create(
        project_id="tmi-test",
        jwks_uri="https://firebase.test/certs",
        timeout_seconds=5,
        http_client=FakeFirebaseClient(public_key),
        clock=lambda: now,
    )

    claims = asyncio.run(verifier.validate_id_token(token))

    assert claims.subject == "firebase-user-1"
    assert claims.email == "owner@example.com"
    assert claims.email_verified is True


def test_firebase_totp_claim_exposes_mfa_evidence() -> None:
    key = rsa.generate_private_key(public_exponent=65_537, key_size=2_048)
    public_key = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    now = datetime(2026, 8, 6, 8, tzinfo=UTC)
    token = jwt.encode(
        {
            "iss": "https://securetoken.google.com/tmi-test",
            "aud": "tmi-test",
            "sub": "firebase-staff-1",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "auth_time": int(now.timestamp()),
            "email": "staff@example.com",
            "email_verified": True,
            "firebase": {
                "sign_in_provider": "google.com",
                "sign_in_second_factor": "totp",
                "second_factor_identifier": "totp-enrollment-1",
            },
        },
        key,
        algorithm="RS256",
        headers={"kid": "firebase-key"},
    )
    verifier = FirebaseTokenVerifier.create(
        project_id="tmi-test",
        jwks_uri="https://firebase.test/certs",
        timeout_seconds=5,
        http_client=FakeFirebaseClient(public_key),
        clock=lambda: now,
    )

    claims = asyncio.run(verifier.validate_id_token(token))

    assert claims.mfa_verified_at == now
    assert claims.second_factor_identifier == "totp-enrollment-1"


def test_unsigned_emulator_token_requires_explicit_local_verifier() -> None:
    now = datetime(2026, 8, 8, 8, tzinfo=UTC)
    token = jwt.encode(
        {
            "iss": "https://securetoken.google.com/tmi-local",
            "aud": "tmi-local",
            "sub": "local-user-1",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "auth_time": int(now.timestamp()),
            "email": "local@example.com",
            "email_verified": True,
            "firebase": {"sign_in_provider": "google.com"},
        },
        key="",
        algorithm="none",
    )
    local_verifier = FirebaseTokenVerifier.create(
        project_id="tmi-local",
        jwks_uri="https://firebase.test/certs",
        timeout_seconds=5,
        emulator_host="firebase-emulator:9099",
        http_client=FakeFirebaseClient("unused"),
        clock=lambda: now,
    )
    production_verifier = FirebaseTokenVerifier.create(
        project_id="tmi-local",
        jwks_uri="https://firebase.test/certs",
        timeout_seconds=5,
        http_client=FakeFirebaseClient("unused"),
        clock=lambda: now,
    )

    claims = asyncio.run(local_verifier.validate_id_token(token))
    assert claims.email == "local@example.com"
    with pytest.raises(OAuthIdentityInvalidError):
        asyncio.run(production_verifier.validate_id_token(token))


def test_local_emulator_preserves_unverified_email_claim() -> None:
    now = datetime(2026, 8, 8, 8, tzinfo=UTC)
    token = jwt.encode(
        {
            "iss": "https://securetoken.google.com/tmi-local",
            "aud": "tmi-local",
            "sub": "local-password-user",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "auth_time": int(now.timestamp()),
            "email": "local@example.com",
            "email_verified": False,
            "firebase": {"sign_in_provider": "password"},
        },
        key="",
        algorithm="none",
    )
    verifier = FirebaseTokenVerifier.create(
        project_id="tmi-local",
        jwks_uri="https://firebase.test/certs",
        timeout_seconds=5,
        emulator_host="firebase-emulator:9099",
        http_client=FakeFirebaseClient("unused"),
        clock=lambda: now,
    )

    claims = asyncio.run(verifier.validate_id_token(token))

    assert claims.email_verified is False
