import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import UUID

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.health import HealthService
from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.main import create_application
from app.modules.auth.dependencies import get_registration_service
from app.modules.auth.models import (
    AccountType,
    Role,
    User,
    UserRole,
    UserStatus,
    VerificationToken,
)
from app.modules.auth.rate_limit import RedisRegistrationRateLimiter
from app.modules.auth.security import (
    Argon2PasswordHasher,
    EncryptedPayload,
    OutboxPayloadCipher,
)
from app.modules.auth.services import (
    InvalidVerificationTokenError,
    RateLimitExceededError,
    RegistrationService,
)


class MutableClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def __call__(self) -> datetime:
        return self.current


class RecordingRateLimiter:
    def __init__(self, *, blocked: bool = False) -> None:
        self.blocked = blocked
        self.calls: list[tuple[str, str]] = []

    async def check(self, *, email: str, client_ip: str) -> None:
        self.calls.append((email, client_ip))
        if self.blocked:
            raise RateLimitExceededError(retry_after_seconds=60)


async def _build_service(
    tmp_path: Path,
    clock: Callable[[], datetime],
    *,
    blocked: bool = False,
) -> tuple[
    RegistrationService,
    async_sessionmaker[AsyncSession],
    OutboxPayloadCipher,
    RecordingRateLimiter,
]:
    database_path = tmp_path / "registration.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session = session_factory()
    cipher = OutboxPayloadCipher(
        key=bytes(range(32)),
        key_id="registration-test-v1",
    )
    limiter = RecordingRateLimiter(blocked=blocked)
    service = RegistrationService(
        session=session,
        password_hasher=Argon2PasswordHasher(),
        payload_cipher=cipher,
        rate_limiter=limiter,
        verification_ttl=timedelta(hours=24),
        clock=clock,
    )
    return service, session_factory, cipher, limiter


async def _outbox_payload(
    session_factory: async_sessionmaker[AsyncSession],
    cipher: OutboxPayloadCipher,
) -> dict[str, str]:
    async with session_factory() as session:
        event = (await session.scalars(select(OutboxEvent))).one()
        plaintext = cipher.decrypt(
            nonce=event.payload_nonce,
            ciphertext=event.payload_ciphertext,
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
        )
    payload: dict[str, str] = json.loads(plaintext)
    return payload


def test_registration_persists_argon2id_token_and_encrypted_outbox(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, cipher, limiter = await _build_service(
            tmp_path,
            clock,
        )

        await service.register(
            email="Owner@TMIGroup.vn",
            password="correct horse battery staple",
            client_ip="203.0.113.10",
        )

        async with session_factory() as session:
            user = (await session.scalars(select(User))).one()
            token = (await session.scalars(select(VerificationToken))).one()
            event = (await session.scalars(select(OutboxEvent))).one()
            assigned_role = await session.scalar(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user.id)
            )

            assert user.email == "owner@tmigroup.vn"
            assert user.status is UserStatus.PENDING
            assert user.password_hash is not None
            assert user.password_hash.startswith("$argon2id$")
            assert token.purpose == "EMAIL_VERIFICATION"
            assert token.expires_at.replace(tzinfo=UTC) == (
                clock.current + timedelta(hours=24)
            )
            assert event.event_type == "user.registered"
            assert event.aggregate_id == user.id
            assert user.account_type is AccountType.INDIVIDUAL_APPLICANT
            assert assigned_role == "USER"
            assert b"owner@tmigroup.vn" not in event.payload_ciphertext

        payload = await _outbox_payload(session_factory, cipher)
        assert payload["email"] == "owner@tmigroup.vn"
        assert payload["user_id"] == str(user.id)
        assert payload["verification_token"]
        assert token.token_hash != payload["verification_token"]
        assert payload["verification_token"].encode() not in event.payload_ciphertext
        assert limiter.calls == [("owner@tmigroup.vn", "203.0.113.10")]

        await service.close()

    asyncio.run(exercise())


def test_public_user_registration_receives_the_viewer_role(tmp_path: Path) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 8, 1, 8, 0, tzinfo=UTC))
        service, session_factory, _, _ = await _build_service(tmp_path, clock)
        await service.register(
            email="viewer@tmigroup.vn",
            password="correct horse battery staple",
            client_ip="203.0.113.20",
            account_type=AccountType.PUBLIC_USER,
        )
        async with session_factory() as session:
            user = (await session.scalars(select(User))).one()
            roles = tuple(
                (
                    await session.scalars(
                        select(Role.code)
                        .join(UserRole, UserRole.role_id == Role.id)
                        .where(UserRole.user_id == user.id)
                    )
                ).all()
            )
            assert user.account_type is AccountType.PUBLIC_USER
            assert roles == ("VIEWER",)
        await service.close()

    asyncio.run(exercise())


def test_registration_rolls_back_when_outbox_encryption_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, cipher, _ = await _build_service(tmp_path, clock)

        def fail_encryption(
            payload: dict[str, str],
            *,
            event_type: str,
            aggregate_id: UUID,
        ) -> EncryptedPayload:
            raise RuntimeError("encryption failed")

        monkeypatch.setattr(cipher, "encrypt", fail_encryption)
        with pytest.raises(RuntimeError, match="encryption failed"):
            await service.register(
                email="rollback@tmigroup.vn",
                password="correct horse battery staple",
                client_ip="203.0.113.10",
            )

        async with session_factory() as session:
            counts = [
                await session.scalar(select(func.count()).select_from(model))
                for model in (User, VerificationToken, OutboxEvent)
            ]
        assert counts == [0, 0, 0]
        await service.close()

    asyncio.run(exercise())


def test_duplicate_registration_returns_without_duplicate_records(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, _, limiter = await _build_service(tmp_path, clock)

        await service.register(
            email="owner@tmigroup.vn",
            password="correct horse battery staple",
            client_ip="203.0.113.10",
        )
        await service.register(
            email="OWNER@TMIGROUP.VN",
            password="a different valid password",
            client_ip="203.0.113.10",
        )

        async with session_factory() as session:
            counts = [
                await session.scalar(select(func.count()).select_from(model))
                for model in (User, VerificationToken, OutboxEvent)
            ]

        assert counts == [1, 1, 1]
        assert len(limiter.calls) == 2
        await service.close()

    asyncio.run(exercise())


def test_verification_token_expires_and_is_one_time(tmp_path: Path) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, cipher, _ = await _build_service(tmp_path, clock)

        await service.register(
            email="first@tmigroup.vn",
            password="correct horse battery staple",
            client_ip="203.0.113.10",
        )
        first_token = (await _outbox_payload(session_factory, cipher))[
            "verification_token"
        ]

        await service.verify_email(first_token)
        with pytest.raises(InvalidVerificationTokenError):
            await service.verify_email(first_token)

        await service.register(
            email="expired@tmigroup.vn",
            password="correct horse battery staple",
            client_ip="203.0.113.11",
        )
        async with session_factory() as session:
            expired_token = next(
                payload["verification_token"]
                for event in (await session.scalars(select(OutboxEvent))).all()
                if (
                    payload := json.loads(
                        cipher.decrypt(
                            nonce=event.payload_nonce,
                            ciphertext=event.payload_ciphertext,
                            event_type=event.event_type,
                            aggregate_id=event.aggregate_id,
                        )
                    )
                )["email"]
                == "expired@tmigroup.vn"
            )

        clock.current += timedelta(hours=25)
        with pytest.raises(InvalidVerificationTokenError):
            await service.verify_email(expired_token)

        async with session_factory() as session:
            users = {
                user.email: user for user in (await session.scalars(select(User))).all()
            }
            assert users["first@tmigroup.vn"].status is UserStatus.ACTIVE
            assert users["first@tmigroup.vn"].email_verified_at is not None
            assert users["expired@tmigroup.vn"].status is UserStatus.PENDING

        await service.close()

    asyncio.run(exercise())


def test_registration_rate_limit_blocks_before_database_write(tmp_path: Path) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, _, limiter = await _build_service(
            tmp_path,
            clock,
            blocked=True,
        )

        with pytest.raises(RateLimitExceededError):
            await service.register(
                email="blocked@tmigroup.vn",
                password="correct horse battery staple",
                client_ip="203.0.113.12",
            )

        async with session_factory() as session:
            count = await session.scalar(select(func.count()).select_from(User))
        assert count == 0
        assert limiter.calls == [("blocked@tmigroup.vn", "203.0.113.12")]
        await service.close()

    asyncio.run(exercise())


class StubRedis:
    def __init__(self, result: list[int]) -> None:
        self.result = result
        self.arguments: tuple[object, ...] = ()

    async def eval(self, *arguments: object) -> list[int]:
        self.arguments = arguments
        return self.result


def test_redis_rate_limit_uses_hashed_dimensions_and_enforces_threshold() -> None:
    async def exercise() -> None:
        client = StubRedis([21, 1, 54])
        limiter = RedisRegistrationRateLimiter(
            cast(Redis, client),
            ip_attempts=20,
            email_attempts=5,
            window_seconds=900,
        )

        with pytest.raises(RateLimitExceededError) as error:
            await limiter.check(
                email="owner@tmigroup.vn",
                client_ip="203.0.113.10",
            )

        serialized_arguments = " ".join(map(str, client.arguments))
        assert "owner@tmigroup.vn" not in serialized_arguments
        assert "203.0.113.10" not in serialized_arguments
        assert error.value.details == {"retry_after_seconds": 54}

    asyncio.run(exercise())


class StubRegistrationService:
    def __init__(self) -> None:
        self.registration: tuple[str, str, str] | None = None
        self.verification_token: str | None = None

    async def register(
        self,
        *,
        email: str,
        password: str,
        client_ip: str,
        account_type: AccountType,
    ) -> None:
        self.registration = (email, password, client_ip)

    async def verify_email(self, token: str) -> None:
        self.verification_token = token


async def _post(
    path: str,
    payload: dict[str, str],
    service: StubRegistrationService,
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_registration_service] = lambda: service
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(path, json=payload)


def test_registration_api_returns_generic_accepted_response() -> None:
    service = StubRegistrationService()
    response = asyncio.run(
        _post(
            "/api/v1/auth/register",
            {
                "email": "Owner@TMIGroup.vn",
                "password": "correct horse battery staple",
                "accountType": "INDIVIDUAL_APPLICANT",
            },
            service,
        )
    )

    assert response.status_code == 202
    assert response.json()["data"] == {
        "message": (
            "If the address can be registered, verification instructions will be sent."
        )
    }
    assert response.json()["meta"]["request_id"] == response.headers["X-Request-ID"]
    assert service.registration == (
        "Owner@tmigroup.vn",
        "correct horse battery staple",
        "127.0.0.1",
    )


def test_verify_email_api_consumes_token() -> None:
    service = StubRegistrationService()
    token = "v" * 43
    response = asyncio.run(
        _post(
            "/api/v1/auth/verify-email",
            {"token": token},
            service,
        )
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "verified"}
    assert service.verification_token == token


def test_registration_api_rejects_short_password_without_echoing_it() -> None:
    service = StubRegistrationService()
    response = asyncio.run(
        _post(
            "/api/v1/auth/register",
            {
                "email": "owner@tmigroup.vn",
                "password": "abcxyz",
                "accountType": "INDIVIDUAL_APPLICANT",
            },
            service,
        )
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "abcxyz" not in response.text
    assert service.registration is None


def test_registration_api_rejects_privileged_council_account_type() -> None:
    service = StubRegistrationService()
    response = asyncio.run(
        _post(
            "/api/v1/auth/register",
            {
                "email": "council@tmigroup.vn",
                "password": "correct horse battery staple",
                "accountType": "COUNCIL_MEMBER",
            },
            service,
        )
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert service.registration is None
