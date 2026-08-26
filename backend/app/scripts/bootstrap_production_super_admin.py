"""Link one existing Firebase identity to the first production Super Admin.

The command never creates a Firebase credential and never accepts a password.
It is an explicit, guarded database bootstrap intended for initial provisioning.
"""

import argparse
import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import delete, select
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
FIREBASE_UID_PATTERN = re.compile(r"[A-Za-z0-9_-]{6,128}")
SUPER_ADMIN_ROLE = "SUPER_ADMIN"
PRODUCTION_CONFIRMATION = "BOOTSTRAP_PRODUCTION_SUPER_ADMIN"


@dataclass(frozen=True, slots=True)
class ProductionFirebaseIdentity:
    email: str
    provider_subject: str


def validate_identity(*, email: str, firebase_uid: str) -> ProductionFirebaseIdentity:
    try:
        normalized_email = str(EMAIL_ADAPTER.validate_python(email)).lower()
    except ValidationError as exc:
        raise ValueError("A valid administrator email is required.") from exc
    uid = firebase_uid.strip()
    if FIREBASE_UID_PATTERN.fullmatch(uid) is None:
        raise ValueError("Firebase UID is invalid.")
    return ProductionFirebaseIdentity(
        email=normalized_email,
        provider_subject=uid,
    )


def require_production_confirmation(settings: Settings, confirmation: str) -> None:
    if settings.app_env != "production":
        raise RuntimeError(
            "Production Super Admin bootstrap requires APP_ENV=production."
        )
    if confirmation != PRODUCTION_CONFIRMATION:
        raise RuntimeError("Production Super Admin confirmation is invalid.")


async def provision_production_super_admin(
    session: AsyncSession,
    identity: ProductionFirebaseIdentity,
) -> UUID:
    """Provision only the first Super Admin and bind the exact Firebase UID."""
    now = datetime.now(UTC)
    async with session.begin():
        role = await session.scalar(select(Role).where(Role.code == SUPER_ADMIN_ROLE))
        if role is None:
            raise RuntimeError(
                "SUPER_ADMIN role is unavailable; run database migrations first."
            )

        identity_owner_id = await session.scalar(
            select(AuthIdentity.user_id).where(
                AuthIdentity.provider == AuthProvider.FIREBASE,
                AuthIdentity.provider_subject == identity.provider_subject,
            )
        )
        user = await session.scalar(select(User).where(User.email == identity.email))
        if identity_owner_id is not None and (
            user is None or identity_owner_id != user.id
        ):
            raise RuntimeError("The Firebase UID is already linked to another account.")

        existing_admin_ids = set(
            (
                await session.scalars(
                    select(UserRole.user_id).where(UserRole.role_id == role.id)
                )
            ).all()
        )
        if existing_admin_ids and (user is None or user.id not in existing_admin_ids):
            raise RuntimeError("SUPER_ADMIN is already assigned to another account.")

        if user is None:
            user = User(
                email=identity.email,
                status=UserStatus.ACTIVE,
                email_verified_at=now,
            )
            session.add(user)
            await session.flush()
        else:
            user.status = UserStatus.ACTIVE
            user.disabled_at = None
            user.deleted_at = None
            user.email_verified_at = user.email_verified_at or now

        firebase_identity = await session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user.id,
                AuthIdentity.provider == AuthProvider.FIREBASE,
            )
        )
        if firebase_identity is None:
            another_provider = await session.scalar(
                select(AuthIdentity.id).where(AuthIdentity.user_id == user.id)
            )
            if another_provider is not None:
                raise RuntimeError(
                    "The account uses another identity provider and cannot be rebound."
                )
            session.add(
                AuthIdentity(
                    user_id=user.id,
                    provider=AuthProvider.FIREBASE,
                    provider_subject=identity.provider_subject,
                )
            )
        elif firebase_identity.provider_subject != identity.provider_subject:
            raise RuntimeError(
                "The supplied Firebase UID does not match the account identity."
            )

        # The consolidated role model assigns one role per person. Bootstrap is
        # explicit and replaces any public role on this initial administrator.
        await session.execute(delete(UserRole).where(UserRole.user_id == user.id))
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.flush()
        return user.id


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Link an existing Firebase user to the first Super Admin."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--firebase-uid", required=True)
    parser.add_argument("--confirm", required=True)
    return parser.parse_args(argv)


async def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    settings = get_settings()
    require_production_confirmation(settings, args.confirm)
    identity = validate_identity(email=args.email, firebase_uid=args.firebase_uid)
    engine = create_runtime_engine(settings)
    try:
        async with create_session_factory(engine)() as session:
            user_id = await provision_production_super_admin(session, identity)
    finally:
        await engine.dispose()
    print(f"Production Super Admin is ready: {identity.email} ({user_id}).")


if __name__ == "__main__":
    asyncio.run(main())
