"""Provision one explicitly requested Super Admin in the local stack only."""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from getpass import getpass

import httpx
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import create_runtime_engine, create_session_factory
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    Role,
    User,
    UserRole,
    UserStatus,
)

EMAIL_ADAPTER = TypeAdapter(EmailStr)
SUPER_ADMIN_ROLE = "SUPER_ADMIN"
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


@dataclass(frozen=True, slots=True)
class LocalFirebaseIdentity:
    email: str
    provider_subject: str


def validate_credentials(*, email: str, password: str) -> tuple[str, str]:
    """Validate operator input without retaining or displaying the password."""
    try:
        normalized_email = str(EMAIL_ADAPTER.validate_python(email)).lower()
    except ValidationError as exc:
        raise ValueError("A valid administrator email is required.") from exc
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError("Administrator password must contain 12 to 128 characters.")
    return normalized_email, password


def require_local_firebase_emulator(settings: Settings) -> str:
    emulator_host = settings.firebase_auth_emulator_host.strip()
    if settings.app_env != "local" or not emulator_host:
        raise RuntimeError(
            "Local Super Admin bootstrap is only available with the Firebase "
            "Auth Emulator."
        )
    return emulator_host


async def provision_firebase_identity(
    *, emulator_host: str, email: str, password: str
) -> LocalFirebaseIdentity:
    """Create or verify a password identity against the local Firebase emulator."""
    base_url = f"http://{emulator_host}/identitytoolkit.googleapis.com/v1/accounts"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{base_url}:signUp?key=local", json=payload)
        if _is_existing_email(response):
            response = await client.post(
                f"{base_url}:signInWithPassword?key=local", json=payload
            )
        response.raise_for_status()
        subject = response.json().get("localId")
    if not isinstance(subject, str) or not subject:
        raise RuntimeError("Firebase Auth Emulator did not return a local identity.")
    return LocalFirebaseIdentity(email=email, provider_subject=subject)


async def provision_super_admin(
    session: AsyncSession, identity: LocalFirebaseIdentity
) -> None:
    """Create an idempotent local Super Admin without promoting another account."""
    now = datetime.now(UTC)
    async with session.begin():
        role = await session.scalar(select(Role).where(Role.code == SUPER_ADMIN_ROLE))
        if role is None:
            raise RuntimeError(
                "SUPER_ADMIN role is unavailable; run database migrations first."
            )

        user = await session.scalar(select(User).where(User.email == identity.email))
        if user is None:
            user = User(
                email=identity.email,
                status=UserStatus.ACTIVE,
                email_verified_at=now,
            )
            session.add(user)
            await session.flush()
        else:
            role_codes = set(
                (
                    await session.scalars(
                        select(Role.code)
                        .join(UserRole, UserRole.role_id == Role.id)
                        .where(UserRole.user_id == user.id)
                    )
                ).all()
            )
            if SUPER_ADMIN_ROLE not in role_codes:
                raise RuntimeError(
                    "The existing account is not a super admin; choose a fresh "
                    "local email instead of promoting it through bootstrap."
                )
            user.status = UserStatus.ACTIVE
            user.email_verified_at = user.email_verified_at or now

        auth_identity = await session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user.id,
                AuthIdentity.provider == AuthProvider.FIREBASE,
            )
        )
        if auth_identity is None:
            existing_identity = await session.scalar(
                select(AuthIdentity.id).where(AuthIdentity.user_id == user.id)
            )
            if existing_identity is not None:
                raise RuntimeError(
                    "The existing Super Admin uses another identity provider and "
                    "cannot be rebound by local bootstrap."
                )
            session.add(
                AuthIdentity(
                    user_id=user.id,
                    provider=AuthProvider.FIREBASE,
                    provider_subject=identity.provider_subject,
                )
            )
        elif auth_identity.provider_subject != identity.provider_subject:
            raise RuntimeError(
                "The Firebase identity does not match the existing Super Admin."
            )

        assignment = await session.get(UserRole, (user.id, role.id))
        if assignment is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one explicitly requested local Super Admin."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password once from standard input instead of prompting.",
    )
    return parser.parse_args(argv)


def read_password(*, from_stdin: bool) -> str:
    if from_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
        if not password:
            raise ValueError("A password must be provided through standard input.")
        return password
    password = getpass("Local Super Admin password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Password confirmation does not match.")
    return password


async def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    email, password = validate_credentials(
        email=args.email,
        password=read_password(from_stdin=args.password_stdin),
    )
    settings = get_settings()
    emulator_host = require_local_firebase_emulator(settings)
    identity = await provision_firebase_identity(
        emulator_host=emulator_host,
        email=email,
        password=password,
    )
    engine = create_runtime_engine(settings)
    try:
        async with create_session_factory(engine)() as session:
            await provision_super_admin(session, identity)
    finally:
        await engine.dispose()
    print(f"Local Super Admin is ready for {identity.email}.")


def _is_existing_email(response: httpx.Response) -> bool:
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    message = error.get("message")
    return isinstance(message, str) and message == "EMAIL_EXISTS"


if __name__ == "__main__":
    asyncio.run(main())
