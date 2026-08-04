import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.modules.auth.errors import InvalidPasswordResetTokenError
from app.modules.auth.models import AuthSession, User, UserStatus, VerificationToken
from app.modules.auth.password_reset_service import PasswordResetService
from app.modules.auth.security import Argon2PasswordHasher, OutboxPayloadCipher


class MutableClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def __call__(self) -> datetime:
        return self.current


class RecordingRateLimiter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def check(self, *, email: str, client_ip: str) -> None:
        self.calls.append((email, client_ip))


async def _build_service(
    tmp_path: Path,
    clock: Callable[[], datetime],
) -> tuple[
    PasswordResetService,
    async_sessionmaker[AsyncSession],
    OutboxPayloadCipher,
    RecordingRateLimiter,
    AsyncEngine,
]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'password-reset.sqlite3').as_posix()}"
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    hasher = Argon2PasswordHasher()
    async with session_factory.begin() as session:
        user = User(
            email="owner@tmigroup.vn",
            password_hash=await hasher.hash("correct horse battery staple"),
            status=UserStatus.ACTIVE,
            email_verified_at=clock(),
        )
        session.add(user)
        await session.flush()
        session.add(
            AuthSession(
                user_id=user.id,
                refresh_token_hash="a" * 64,
                expires_at=clock() + timedelta(days=30),
            )
        )

    cipher = OutboxPayloadCipher(key=bytes(range(32)), key_id="reset-test-v1")
    limiter = RecordingRateLimiter()
    return (
        PasswordResetService(
            session=session_factory(),
            password_hasher=hasher,
            payload_cipher=cipher,
            rate_limiter=limiter,
            reset_ttl=timedelta(hours=1),
            clock=clock,
        ),
        session_factory,
        cipher,
        limiter,
        engine,
    )


async def _reset_token(
    session_factory: async_sessionmaker[AsyncSession],
    cipher: OutboxPayloadCipher,
) -> str:
    async with session_factory() as session:
        event = (await session.scalars(select(OutboxEvent))).one()
        payload: dict[str, str] = json.loads(
            cipher.decrypt(
                nonce=event.payload_nonce,
                ciphertext=event.payload_ciphertext,
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
            )
        )
    return payload["reset_token"]


def test_unknown_email_is_safe_and_returns_without_records(tmp_path: Path) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, _, limiter, engine = await _build_service(
            tmp_path,
            clock,
        )

        await service.request_reset(
            email="UNKNOWN@tmigroup.vn",
            client_ip="203.0.113.10",
        )

        async with session_factory() as session:
            tokens = (await session.scalars(select(VerificationToken))).all()
            events = (await session.scalars(select(OutboxEvent))).all()
        assert tokens == []
        assert events == []
        assert limiter.calls == [("unknown@tmigroup.vn", "203.0.113.10")]
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_reset_token_is_hashed_and_outbox_payload_is_encrypted(tmp_path: Path) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, cipher, _, engine = await _build_service(
            tmp_path,
            clock,
        )

        await service.request_reset(
            email="owner@tmigroup.vn",
            client_ip="203.0.113.10",
        )
        raw_token = await _reset_token(session_factory, cipher)

        async with session_factory() as session:
            token = (await session.scalars(select(VerificationToken))).one()
            event = (await session.scalars(select(OutboxEvent))).one()
        assert token.purpose == "PASSWORD_RESET"
        assert token.token_hash != raw_token
        assert token.expires_at.replace(tzinfo=UTC) == (
            clock.current + timedelta(hours=1)
        )
        assert event.event_type == "user.password_reset_requested"
        assert raw_token.encode() not in event.payload_ciphertext
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_reset_consumes_token_changes_password_and_revokes_sessions(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, cipher, _, engine = await _build_service(
            tmp_path,
            clock,
        )
        await service.request_reset(
            email="owner@tmigroup.vn",
            client_ip="203.0.113.10",
        )
        raw_token = await _reset_token(session_factory, cipher)

        await service.reset_password(
            token=raw_token,
            new_password="new correct horse battery staple",
        )

        async with session_factory() as session:
            user = (await session.scalars(select(User))).one()
            verification = (await session.scalars(select(VerificationToken))).one()
            auth_session = (await session.scalars(select(AuthSession))).one()
        assert user.password_hash is not None
        assert await Argon2PasswordHasher().verify(
            user.password_hash,
            "new correct horse battery staple",
        )
        assert verification.consumed_at is not None
        assert auth_session.revoked_at is not None

        with pytest.raises(InvalidPasswordResetTokenError):
            await service.reset_password(
                token=raw_token,
                new_password="another correct horse battery",
            )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_expired_reset_token_is_rejected_without_changing_password(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime(2026, 7, 30, 8, 0, tzinfo=UTC))
        service, session_factory, cipher, _, engine = await _build_service(
            tmp_path,
            clock,
        )
        await service.request_reset(
            email="owner@tmigroup.vn",
            client_ip="203.0.113.10",
        )
        raw_token = await _reset_token(session_factory, cipher)
        clock.current += timedelta(hours=2)

        with pytest.raises(InvalidPasswordResetTokenError):
            await service.reset_password(
                token=raw_token,
                new_password="new correct horse battery staple",
            )

        async with session_factory() as session:
            user = (await session.scalars(select(User))).one()
            auth_session = (await session.scalars(select(AuthSession))).one()
        assert user.password_hash is not None
        assert await Argon2PasswordHasher().verify(
            user.password_hash,
            "correct horse battery staple",
        )
        assert auth_session.revoked_at is None
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
