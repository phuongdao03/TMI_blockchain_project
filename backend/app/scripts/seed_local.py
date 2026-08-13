import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import create_runtime_engine, create_session_factory
from app.modules.auth.models import (
    AccountType,
    AuthIdentity,
    AuthProvider,
    Role,
    User,
    UserRole,
    UserStatus,
)

LOCAL_IDENTITIES = (
    ("applicant@example.com", "APPLICANT", AccountType.INDIVIDUAL_APPLICANT),
    ("reviewer@example.com", "REVIEWER", None),
    ("council@example.com", "COUNCIL_MEMBER", None),
    ("admin@example.com", "SUPER_ADMIN", None),
)


@dataclass(frozen=True, slots=True)
class LocalIdentity:
    email: str
    provider_subject: str
    role_code: str
    account_type: AccountType | None


async def provision_firebase_identities(
    *, emulator_host: str, password: str
) -> tuple[LocalIdentity, ...]:
    base_url = f"http://{emulator_host}/identitytoolkit.googleapis.com/v1/accounts"
    identities: list[LocalIdentity] = []
    async with httpx.AsyncClient(timeout=10) as client:
        for email, role_code, account_type in LOCAL_IDENTITIES:
            payload = {"email": email, "password": password, "returnSecureToken": True}
            response = await client.post(f"{base_url}:signUp?key=local", json=payload)
            if (
                response.status_code == 400
                and response.json().get("error", {}).get("message") == "EMAIL_EXISTS"
            ):
                response = await client.post(
                    f"{base_url}:signInWithPassword?key=local", json=payload
                )
            response.raise_for_status()
            subject = response.json().get("localId")
            if not isinstance(subject, str) or not subject:
                raise RuntimeError(
                    f"Firebase emulator did not return localId for {email}."
                )
            identities.append(LocalIdentity(email, subject, role_code, account_type))
    return tuple(identities)


async def seed_database(
    session: AsyncSession, identities: tuple[LocalIdentity, ...]
) -> None:
    now = datetime.now(UTC)
    for identity in identities:
        user = await session.scalar(select(User).where(User.email == identity.email))
        if user is None:
            user = User(
                email=identity.email,
                status=UserStatus.ACTIVE,
                email_verified_at=now,
                account_type=identity.account_type,
            )
            session.add(user)
            await session.flush()
        else:
            user.status = UserStatus.ACTIVE
            user.email_verified_at = user.email_verified_at or now
            user.account_type = identity.account_type

        auth_identity = await session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user.id,
                AuthIdentity.provider == AuthProvider.FIREBASE,
            )
        )
        if auth_identity is None:
            session.add(
                AuthIdentity(
                    user_id=user.id,
                    provider=AuthProvider.FIREBASE,
                    provider_subject=identity.provider_subject,
                )
            )
        else:
            auth_identity.provider_subject = identity.provider_subject

        role = await session.scalar(select(Role).where(Role.code == identity.role_code))
        if role is None:
            role = Role(code=identity.role_code)
            session.add(role)
            await session.flush()
        assignment = await session.get(UserRole, (user.id, role.id))
        if assignment is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.commit()


async def main() -> None:
    settings = get_settings()
    if settings.app_env != "local" or not settings.firebase_auth_emulator_host:
        raise RuntimeError("Local seed is only available with Firebase Auth Emulator.")
    password = os.environ.get("LOCAL_SEED_PASSWORD", "LocalOnly!23456")
    identities = await provision_firebase_identities(
        emulator_host=settings.firebase_auth_emulator_host,
        password=password,
    )
    engine = create_runtime_engine(settings)
    try:
        async with create_session_factory(engine)() as session:
            await seed_database(session, identities)
    finally:
        await engine.dispose()
    print(f"Seeded {len(identities)} local identities.")


if __name__ == "__main__":
    asyncio.run(main())
