import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import main as application_models  # noqa: F401
from app.core.errors import DomainError
from app.db.base import Base
from app.modules.auth.firebase_provider import FirebaseClaims
from app.modules.auth.models import AuthIdentity, AuthProvider, User, UserStatus
from app.modules.auth.session_service import ClientMetadata, IssuedSession
from app.modules.auth.username_login import (
    FirebasePasswordGateway,
    UsernameLoginService,
)
from app.modules.community.models import CommunityProfile


def test_username_rate_limit_precedes_account_lookup():
    async def scenario():
        limiter = SimpleNamespace(check=AsyncMock(side_effect=RuntimeError("limited")))
        session = SimpleNamespace(begin=AsyncMock())
        service = UsernameLoginService(
            session=session,
            sessions=SimpleNamespace(),
            passwords=SimpleNamespace(),
            verifier=SimpleNamespace(),
            rate_limiter=limiter,
        )
        with pytest.raises(RuntimeError, match="limited"):
            await service.login(
                username=" OWNER ",
                password="private-credential",
                metadata=ClientMetadata("127.0.0.1", None, None),
            )
        limiter.check.assert_awaited_once_with(email="owner", client_ip="127.0.0.1")
        session.begin.assert_not_called()

    asyncio.run(scenario())


def test_username_endpoint_issues_existing_secure_session_cookies():
    from app.core.config import Settings, get_settings
    from app.core.health import HealthService
    from app.main import create_application
    from app.modules.auth.dependencies import (
        get_session_service,
        get_username_login_service,
    )
    from app.modules.auth.models import AccountType
    from app.modules.auth.session_service import AuthPrincipal

    async def scenario():
        settings = Settings(app_env="local")
        app = create_application(settings=settings, health_service=HealthService({}))
        principal = AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="private@example.vn",
            roles=("USER",),
            account_type=AccountType.INDIVIDUAL_APPLICANT,
        )
        service = SimpleNamespace(
            login=AsyncMock(return_value=IssuedSession("access", "refresh", "csrf"))
        )
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_username_login_service] = lambda: service
        app.dependency_overrides[get_session_service] = lambda: SimpleNamespace(
            authenticate_access=AsyncMock(return_value=principal)
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                response = await client.post(
                    "/api/v1/auth/username-login",
                    json={"username": "lan_anh", "password": "private-credential"},
                )
                assert response.status_code == 200
                cookies = response.headers.get_list("set-cookie")
                assert any("cns_access=" in c and "HttpOnly" in c for c in cookies)
                assert any("cns_refresh=" in c and "HttpOnly" in c for c in cookies)
                assert "private-credential" not in response.text
                assert "provider-token" not in response.text

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "case",
    [
        "firebase",
        "local",
        "unknown",
        "disabled",
        "unverified",
        "wrong_subject",
        "wrong_email",
        "unverified_token",
    ],
)
def test_username_authentication_preserves_identity_and_session_checks(case):
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            owner = uuid4()
            session.add(
                User(
                    id=owner,
                    email="owner@example.vn",
                    status=UserStatus.ACTIVE,
                    email_verified_at=None
                    if case == "unverified"
                    else datetime.now(UTC),
                    disabled_at=datetime.now(UTC) if case == "disabled" else None,
                    password_hash="local-hash" if case == "local" else None,
                )
            )
            await session.flush()
            session.add_all(
                [
                    CommunityProfile(user_id=owner, username="lan_anh"),
                    AuthIdentity(
                        user_id=owner,
                        provider=AuthProvider.FIREBASE,
                        provider_subject="firebase-owner",
                    ),
                ]
            )
            await session.commit()
            issued = IssuedSession("access", "refresh", "csrf")
            sessions = SimpleNamespace(
                login=AsyncMock(return_value=issued),
                issue_for_user=AsyncMock(return_value=issued),
            )
            passwords = SimpleNamespace(
                id_token=AsyncMock(return_value="provider-token")
            )
            claims = FirebaseClaims(
                subject="other" if case == "wrong_subject" else "firebase-owner",
                email="other@example.vn"
                if case == "wrong_email"
                else "owner@example.vn",
                email_verified=case != "unverified_token",
                name=None,
                picture=None,
            )
            verifier = SimpleNamespace(validate_id_token=AsyncMock(return_value=claims))
            limiter = SimpleNamespace(check=AsyncMock())
            service = UsernameLoginService(
                session=session,
                sessions=sessions,
                passwords=passwords,
                verifier=verifier,
                rate_limiter=limiter,
            )
            arguments = dict(
                username="missing" if case == "unknown" else " LAN_ANH ",
                password="correct-password",
                metadata=ClientMetadata("127.0.0.1", None, None),
            )
            if case in {"firebase", "local"}:
                assert await service.login(**arguments) == issued
                if case == "local":
                    sessions.login.assert_awaited_once()
                    passwords.id_token.assert_not_awaited()
                else:
                    passwords.id_token.assert_awaited_once_with(
                        "owner@example.vn", "correct-password"
                    )
                    sessions.issue_for_user.assert_awaited_once_with(
                        user_id=owner, metadata=arguments["metadata"]
                    )
            else:
                with pytest.raises(DomainError) as error:
                    await service.login(**arguments)
                assert error.value.code == "INVALID_CREDENTIALS"
                sessions.issue_for_user.assert_not_awaited()
                sessions.login.assert_not_awaited()
            limiter.check.assert_awaited_once()
        await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "status,payload,expected",
    [
        (200, {"idToken": "token"}, "token"),
        (400, {"error": {"message": "INVALID_PASSWORD"}}, "INVALID_CREDENTIALS"),
        (200, {"mfaPendingCredential": "mfa"}, "INVALID_CREDENTIALS"),
        (429, {}, "RATE_LIMITED"),
        (503, {}, "OAUTH_PROVIDER_UNAVAILABLE"),
    ],
)
def test_firebase_password_gateway_handles_errors_without_exposing_credentials(
    status, payload, expected
):
    async def scenario():
        def respond(request):
            assert request.url.host == "identitytoolkit.googleapis.com"
            return httpx.Response(status, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            gateway = FirebasePasswordGateway(
                client=client, api_key="test-public-api-key", timeout_seconds=2
            )
            if expected == "token":
                assert (
                    await gateway.id_token(
                        "owner@example.vn", "private-test-credential!"
                    )
                    == "token"
                )
            else:
                with pytest.raises(DomainError) as error:
                    await gateway.id_token(
                        "owner@example.vn", "private-test-credential!"
                    )
                assert error.value.code == expected
                assert "owner@example.vn" not in str(error.value)
                assert "private-test-credential!" not in str(error.value)

    asyncio.run(scenario())
