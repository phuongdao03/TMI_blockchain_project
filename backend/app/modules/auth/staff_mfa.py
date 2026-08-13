from collections.abc import Collection
from datetime import UTC, datetime, timedelta

from app.core.errors import DomainError
from app.modules.auth.schemas import INTERNAL_MANAGED_ROLES

PRIVILEGED_STAFF_ROLES = INTERNAL_MANAGED_ROLES | {"SUPER_ADMIN"}


class StaffMfaPolicy:
    def __init__(self, *, max_age: timedelta, enabled: bool = True) -> None:
        self._max_age = max_age
        self._enabled = enabled

    @staticmethod
    def is_required(roles: Collection[str]) -> bool:
        return bool(PRIVILEGED_STAFF_ROLES.intersection(roles))

    def require(
        self,
        *,
        roles: Collection[str],
        mfa_verified_at: datetime | None,
        now: datetime,
    ) -> None:
        if not self._enabled or not self.is_required(roles):
            return
        if mfa_verified_at is None:
            raise DomainError(
                code="STAFF_MFA_REQUIRED",
                message="Additional account verification is required.",
                status_code=403,
            )
        verified_at = self._as_utc(mfa_verified_at)
        if verified_at > now or verified_at + self._max_age <= now:
            raise DomainError(
                code="STAFF_MFA_REAUTH_REQUIRED",
                message="Additional account verification must be renewed.",
                status_code=403,
            )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
