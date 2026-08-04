import asyncio
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
from app.modules.auth.models import AuthSession, User, UserStatus
from app.modules.auth.security import Argon2PasswordHasher
from app.modules.auth.session_service import (
    ClientMetadata,
    InvalidCredentialsError,
    SessionService,
    UnauthenticatedError,
)
from app.modules.auth.tokens import AccessTokenManager, CsrfTokenManager


class MutableClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def __call__(self) -> datetime:
        return self.current


class RecordingLoginRateLimiter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def check(self, *, email: str, client_ip: str) -> None:
        self.calls.append((email, client_ip))


async def _build_session_service(
    tmp_path: Path,
    clock: Callable[[], datetime],
) -> tuple[
    SessionService,
    async_sessionmaker[AsyncSession],
    RecordingLoginRateLimiter,
    AsyncEngine,
]:
    database_path = tmp_path / "sessions.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    password_hasher = Argon2PasswordHasher()
    async with session_factory.begin() as session:
        session.add(
            User(
                email="owner@tmigroup.vn",
                password_hash=await password_hasher.hash(
                    "correct horse battery staple"
                ),
                status=UserStatus.ACTIVE,
                email_verified_at=clock(),
            )
        )

    limiter = RecordingLoginRateLimiter()
    service = SessionService(
        session=session_factory(),
        password_hasher=password_hasher,
        access_tokens=AccessTokenManager(
            secret="a" * 64,
            issuer="tmi-platform",
            audience="tmi-web",
            ttl=timedelta(minutes=15),
            clock=clock,
        ),
        csrf_tokens=CsrfTokenManager(secret="b" * 64),
        rate_limiter=limiter,
        refresh_ttl=timedelta(days=30),
        clock=clock,
    )
    return service, session_factory, limiter, engine


def test_login_creates_hashed_refresh_session_and_short_access_token(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime.now(UTC).replace(microsecond=0))
        service, session_factory, limiter, engine = await _build_session_service(
            tmp_path,
            clock,
        )
        metadata = ClientMetadata(
            client_ip="203.0.113.10",
            user_agent="TMI test browser",
            device_name="Work laptop",
        )

        issued = await service.login(
            email="OWNER@TMIGROUP.VN",
            password="correct horse battery staple",
            metadata=metadata,
        )
        principal = await service.authenticate_access(issued.access_token)

        async with session_factory() as session:
            user = (await session.scalars(select(User))).one()
            auth_session = (await session.scalars(select(AuthSession))).one()

        assert issued.refresh_token not in auth_session.refresh_token_hash
        assert auth_session.refresh_token_hash
        assert auth_session.user_id == user.id
        assert auth_session.device_name == "Work laptop"
        assert auth_session.user_agent == "TMI test browser"
        assert auth_session.ip_hash != metadata.client_ip
        assert auth_session.expires_at.replace(tzinfo=UTC) == (
            clock.current + timedelta(days=30)
        )
        assert principal.user_id == user.id
        assert principal.session_id == auth_session.id
        assert principal.email == "owner@tmigroup.vn"
        assert principal.roles == ()
        assert issued.csrf_token
        assert limiter.calls == [("owner@tmigroup.vn", "203.0.113.10")]

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_provider_only_user_cannot_use_password_login(tmp_path: Path) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime.now(UTC).replace(microsecond=0))
        service, session_factory, _, engine = await _build_session_service(
            tmp_path,
            clock,
        )
        async with session_factory.begin() as session:
            user = (await session.scalars(select(User))).one()
            user.password_hash = None

        with pytest.raises(InvalidCredentialsError):
            await service.login(
                email="owner@tmigroup.vn",
                password="correct horse battery staple",
                metadata=ClientMetadata(
                    client_ip="203.0.113.10",
                    user_agent="TMI test browser",
                    device_name="Work laptop",
                ),
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_refresh_rotates_token_and_reuse_revokes_every_session(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime.now(UTC).replace(microsecond=0))
        service, session_factory, _, engine = await _build_session_service(
            tmp_path,
            clock,
        )
        metadata = ClientMetadata(
            client_ip="203.0.113.10",
            user_agent="TMI test browser",
            device_name="Work laptop",
        )
        first = await service.login(
            email="owner@tmigroup.vn",
            password="correct horse battery staple",
            metadata=metadata,
        )

        second = await service.refresh(
            refresh_token=first.refresh_token,
            csrf_cookie=first.csrf_token,
            csrf_header=first.csrf_token,
            metadata=metadata,
        )

        async with session_factory() as session:
            sessions = (
                await session.scalars(
                    select(AuthSession).order_by(AuthSession.created_at)
                )
            ).all()
        assert len(sessions) == 2
        old_session, new_session = sessions
        assert old_session.revoked_at is not None
        assert new_session.revoked_at is None
        assert new_session.rotated_from_id == old_session.id
        assert second.refresh_token != first.refresh_token
        assert second.csrf_token != first.csrf_token
        assert (await service.authenticate_access(second.access_token)).session_id == (
            new_session.id
        )

        with pytest.raises(UnauthenticatedError):
            await service.refresh(
                refresh_token=first.refresh_token,
                csrf_cookie=first.csrf_token,
                csrf_header=first.csrf_token,
                metadata=metadata,
            )

        async with session_factory() as session:
            revoked_at_values = (
                await session.scalars(select(AuthSession.revoked_at))
            ).all()
        assert all(revoked_at is not None for revoked_at in revoked_at_values)
        with pytest.raises(UnauthenticatedError):
            await service.authenticate_access(second.access_token)

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_session_listing_revoke_and_logout_are_user_scoped(tmp_path: Path) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime.now(UTC).replace(microsecond=0))
        service, _, _, engine = await _build_session_service(tmp_path, clock)
        first = await service.login(
            email="owner@tmigroup.vn",
            password="correct horse battery staple",
            metadata=ClientMetadata(
                client_ip="203.0.113.10",
                user_agent="Browser one",
                device_name="Laptop",
            ),
        )
        second = await service.login(
            email="owner@tmigroup.vn",
            password="correct horse battery staple",
            metadata=ClientMetadata(
                client_ip="203.0.113.11",
                user_agent="Browser two",
                device_name="Phone",
            ),
        )
        first_principal = await service.authenticate_access(first.access_token)
        second_principal = await service.authenticate_access(second.access_token)

        sessions = await service.list_sessions(first_principal)
        assert len(sessions) == 2
        assert sum(item.is_current for item in sessions) == 1
        assert {item.device_name for item in sessions} == {"Laptop", "Phone"}

        await service.revoke_session(
            principal=first_principal,
            target_session_id=second_principal.session_id,
            csrf_cookie=first.csrf_token,
            csrf_header=first.csrf_token,
        )
        with pytest.raises(UnauthenticatedError):
            await service.authenticate_access(second.access_token)

        await service.logout(
            refresh_token=first.refresh_token,
            csrf_cookie=first.csrf_token,
            csrf_header=first.csrf_token,
        )
        with pytest.raises(UnauthenticatedError):
            await service.authenticate_access(first.access_token)

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("owner@tmigroup.vn", "wrong password value"),
        ("unknown@tmigroup.vn", "correct horse battery staple"),
    ],
)
def test_login_returns_same_error_for_wrong_password_and_unknown_email(
    tmp_path: Path,
    email: str,
    password: str,
) -> None:
    async def exercise() -> None:
        clock = MutableClock(datetime.now(UTC).replace(microsecond=0))
        service, session_factory, _, engine = await _build_session_service(
            tmp_path,
            clock,
        )

        with pytest.raises(InvalidCredentialsError) as error:
            await service.login(
                email=email,
                password=password,
                metadata=ClientMetadata(
                    client_ip="203.0.113.10",
                    user_agent=None,
                    device_name=None,
                ),
            )

        async with session_factory() as session:
            assert (await session.scalars(select(AuthSession))).all() == []
        assert error.value.code == "INVALID_CREDENTIALS"
        assert error.value.message == "Email or password is incorrect."

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
