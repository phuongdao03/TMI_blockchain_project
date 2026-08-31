"""Perform one audited Firebase email-verification bootstrap for Super Admin.

This command does not create identities, rebind Firebase UIDs, change roles, or
alter normal email-verification policy. It is intentionally limited to an
existing, active, exact Firebase-backed Super Admin in production.
"""

import argparse
import asyncio
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import create_runtime_engine, create_session_factory
from app.modules.audit.service import AuditService
from app.modules.auth.firebase_admin_gateway import (
    FirebaseAdminGateway,
    FirebaseEmailVerificationClient,
)
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    AuthSession,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.scripts.bootstrap_production_super_admin import (
    ProductionFirebaseIdentity,
    validate_identity,
)

SUPER_ADMIN_ROLE = "SUPER_ADMIN"
VERIFICATION_CONFIRMATION = "VERIFY_PRODUCTION_SUPER_ADMIN_FIREBASE_EMAIL"
VERIFICATION_ACTOR_SERVICE = "production-firebase-email-verification-bootstrap"


@dataclass(frozen=True, slots=True)
class ProductionEmailVerificationResult:
    user_id: UUID
    email_verified_changed: bool


def require_production_verification_confirmation(
    settings: Settings, confirmation: str
) -> None:
    if settings.app_env != "production":
        raise RuntimeError(
            "Production Firebase email verification requires APP_ENV=production."
        )
    if confirmation != VERIFICATION_CONFIRMATION:
        raise RuntimeError(
            "Production Firebase email verification confirmation is invalid."
        )


def require_temporary_admin_credentials() -> None:
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path or not Path(credentials_path).is_file():
        raise RuntimeError(
            "A mounted Firebase Admin credential file is required through "
            "GOOGLE_APPLICATION_CREDENTIALS."
        )


async def _require_exact_active_super_admin(
    session: AsyncSession,
    identity: ProductionFirebaseIdentity,
) -> User:
    user = await session.scalar(select(User).where(User.email == identity.email))
    if user is None:
        raise RuntimeError("The supplied email is not an application account.")
    if (
        user.status is not UserStatus.ACTIVE
        or user.disabled_at is not None
        or user.deleted_at is not None
    ):
        raise RuntimeError("The supplied account is not active.")

    firebase_subject = await session.scalar(
        select(AuthIdentity.provider_subject).where(
            AuthIdentity.user_id == user.id,
            AuthIdentity.provider == AuthProvider.FIREBASE,
        )
    )
    if firebase_subject != identity.provider_subject:
        raise RuntimeError("The supplied Firebase UID does not match the account.")

    has_super_admin_role = await session.scalar(
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user.id, Role.code == SUPER_ADMIN_ROLE)
    )
    if has_super_admin_role is None:
        raise RuntimeError("The supplied account is not a SUPER_ADMIN.")
    return user


async def verify_production_super_admin_email(
    session: AsyncSession,
    identity: ProductionFirebaseIdentity,
    *,
    firebase_admin: FirebaseEmailVerificationClient,
    audit: AuditService | None = None,
) -> ProductionEmailVerificationResult:
    """Set Firebase email_verified for one exact, active Super Admin identity."""
    operation_id = str(uuid4())
    audit_service = audit or AuditService(session)
    async with session.begin():
        target = await _require_exact_active_super_admin(session, identity)
        user_id = target.id
        audit_service.record(
            actor_user_id=None,
            actor_service=VERIFICATION_ACTOR_SERVICE,
            action="production.firebase_identity.email_verification_requested",
            resource_type="user",
            resource_id=str(target.id),
            before={
                "application_verification": target.email_verified_at is not None,
            },
            after={"operation_id": operation_id},
        )
        await session.flush()

    try:
        changed = await firebase_admin.verify_email_for_identity(
            identity.provider_subject,
            expected_email=identity.email,
        )
        # Always revoke after a verified lookup. A previous partial run may
        # already have updated Firebase but failed before local session work.
        await firebase_admin.revoke_refresh_tokens(identity.provider_subject)
    except Exception:
        async with session.begin():
            target = await _require_exact_active_super_admin(session, identity)
            audit_service.record(
                actor_user_id=None,
                actor_service=VERIFICATION_ACTOR_SERVICE,
                action="production.firebase_identity.email_verification_reconciliation_needed",
                resource_type="user",
                resource_id=str(target.id),
                after={
                    "operation_id": operation_id,
                    "retry_required": True,
                },
            )
            await session.flush()
        raise

    now = datetime.now(UTC)
    async with session.begin():
        target = await _require_exact_active_super_admin(session, identity)
        application_verification_before = target.email_verified_at is not None
        target.email_verified_at = target.email_verified_at or now
        await session.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == target.id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        audit_service.record(
            actor_user_id=None,
            actor_service=VERIFICATION_ACTOR_SERVICE,
            action="production.firebase_identity.email_verification_completed",
            resource_type="user",
            resource_id=str(target.id),
            before={
                "firebase_verification": not changed,
                "application_verification": application_verification_before,
            },
            after={
                "firebase_verification": True,
                "application_verification": True,
                "firebase_updated": changed,
                "sessions_revoked": True,
                "operation_id": operation_id,
            },
        )
        await session.flush()
    return ProductionEmailVerificationResult(
        user_id=user_id,
        email_verified_changed=changed,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify one exact production Firebase Super Admin email."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--firebase-uid", required=True)
    parser.add_argument("--confirm", required=True)
    return parser.parse_args(argv)


async def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    settings = get_settings()
    require_production_verification_confirmation(settings, args.confirm)
    require_temporary_admin_credentials()
    identity = validate_identity(email=args.email, firebase_uid=args.firebase_uid)
    firebase_admin = FirebaseAdminGateway.create(settings)
    engine = create_runtime_engine(settings)
    try:
        async with create_session_factory(engine)() as session:
            result = await verify_production_super_admin_email(
                session,
                identity,
                firebase_admin=firebase_admin,
            )
    finally:
        await engine.dispose()
    result_label = (
        "updated Firebase and revoked existing sessions"
        if result.email_verified_changed
        else "was already verified in Firebase; sessions were reconciled and revoked"
    )
    print(
        "Production Firebase email verification completed: "
        f"{result.user_id}; {result_label}."
    )


if __name__ == "__main__":
    asyncio.run(main())
