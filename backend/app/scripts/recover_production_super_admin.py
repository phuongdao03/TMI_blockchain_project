"""Recover the production Super Admin after the prior Firebase account is gone.

This command is deliberately separate from first-time bootstrap. It preserves
the former administrator and audit history in the database, but removes their
application access before assigning the supplied Firebase identity as the sole
Super Admin.
"""

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import create_runtime_engine, create_session_factory
from app.modules.audit.service import AuditService
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
RECOVERY_CONFIRMATION = "RECOVER_PRODUCTION_SUPER_ADMIN_AFTER_FIREBASE_DELETION"
RECOVERY_ACTOR_SERVICE = "production-super-admin-recovery"


@dataclass(frozen=True, slots=True)
class ProductionSuperAdminRecoveryResult:
    user_id: UUID
    decommissioned_user_ids: tuple[UUID, ...]


def require_production_recovery_confirmation(
    settings: Settings, confirmation: str
) -> None:
    if settings.app_env != "production":
        raise RuntimeError(
            "Production Super Admin recovery requires APP_ENV=production."
        )
    if confirmation != RECOVERY_CONFIRMATION:
        raise RuntimeError("Production Super Admin recovery confirmation is invalid.")


async def recover_production_super_admin(
    session: AsyncSession,
    identity: ProductionFirebaseIdentity,
    *,
    audit: AuditService | None = None,
) -> ProductionSuperAdminRecoveryResult:
    """Make ``identity`` the sole active Super Admin and retire predecessors."""
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

        existing_admin_ids = tuple(
            (
                await session.scalars(
                    select(UserRole.user_id).where(UserRole.role_id == role.id)
                )
            ).all()
        )
        decommissioned_user_ids = tuple(
            user_id for user_id in existing_admin_ids if user_id != user.id
        )

        if decommissioned_user_ids:
            await session.execute(
                delete(UserRole).where(
                    UserRole.role_id == role.id,
                    UserRole.user_id.in_(decommissioned_user_ids),
                )
            )
            await session.execute(
                update(User)
                .where(User.id.in_(decommissioned_user_ids))
                .values(
                    status=UserStatus.DELETED,
                    disabled_at=now,
                    deleted_at=now,
                )
            )
            await session.execute(
                update(AuthSession)
                .where(
                    AuthSession.user_id.in_(decommissioned_user_ids),
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )

        await session.execute(delete(UserRole).where(UserRole.user_id == user.id))
        session.add(UserRole(user_id=user.id, role_id=role.id))

        audit_service = audit or AuditService(session)
        for old_user_id in decommissioned_user_ids:
            audit_service.record(
                actor_user_id=None,
                actor_service=RECOVERY_ACTOR_SERVICE,
                action="production.super_admin.decommissioned",
                resource_type="user",
                resource_id=str(old_user_id),
                before={"role": SUPER_ADMIN_ROLE, "status": UserStatus.ACTIVE.value},
                after={"role": None, "status": UserStatus.DELETED.value},
            )
        audit_service.record(
            actor_user_id=None,
            actor_service=RECOVERY_ACTOR_SERVICE,
            action="production.super_admin.recovered",
            resource_type="user",
            resource_id=str(user.id),
            before={"role": None},
            after={"role": SUPER_ADMIN_ROLE},
        )
        await session.flush()
        return ProductionSuperAdminRecoveryResult(
            user_id=user.id,
            decommissioned_user_ids=decommissioned_user_ids,
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recover the sole production Super Admin after Firebase deletion."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--firebase-uid", required=True)
    parser.add_argument("--confirm", required=True)
    return parser.parse_args(argv)


async def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    settings = get_settings()
    require_production_recovery_confirmation(settings, args.confirm)
    identity = validate_identity(email=args.email, firebase_uid=args.firebase_uid)
    engine = create_runtime_engine(settings)
    try:
        async with create_session_factory(engine)() as session:
            result = await recover_production_super_admin(session, identity)
    finally:
        await engine.dispose()
    print(
        "Production Super Admin recovery completed: "
        f"{identity.email} ({result.user_id}); "
        f"retired {len(result.decommissioned_user_ids)} prior Super Admin account(s)."
    )


if __name__ == "__main__":
    asyncio.run(main())
