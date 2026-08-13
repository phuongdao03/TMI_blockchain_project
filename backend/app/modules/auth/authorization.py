from collections.abc import Callable
from dataclasses import dataclass

from app.modules.auth.session_service import AuthPrincipal

ErrorFactory = Callable[[], Exception]


@dataclass(frozen=True, slots=True)
class PolicyRequirement:
    """A server-owned capability rule.

    ``compatible_roles`` keeps existing role assignments working while the
    normalized permission catalog is rolled out. Both values come from the
    authenticated server-side principal; client claims are never consulted.
    """

    permission: str
    compatible_roles: frozenset[str] = frozenset()
    allow_super_admin: bool = True

    def __post_init__(self) -> None:
        if not self.permission.strip():
            raise ValueError("Policy permission must not be empty.")


class AuthorizationPolicy:
    @staticmethod
    def allows_capability(
        principal: AuthPrincipal,
        requirement: PolicyRequirement,
    ) -> bool:
        has_permission = requirement.permission in principal.permissions
        has_compatible_role = not requirement.compatible_roles.isdisjoint(
            principal.roles
        )
        is_super_admin = (
            requirement.allow_super_admin and "SUPER_ADMIN" in principal.roles
        )
        return has_permission or has_compatible_role or is_super_admin

    @staticmethod
    def require_capability(
        principal: AuthPrincipal,
        requirement: PolicyRequirement,
        denied: ErrorFactory,
    ) -> None:
        if not AuthorizationPolicy.allows_capability(principal, requirement):
            raise denied()

    @staticmethod
    def require_resource_scope(allowed: bool, denied: ErrorFactory) -> None:
        if not allowed:
            raise denied()

    @staticmethod
    def require_business_state(allowed: bool, denied: ErrorFactory) -> None:
        if not allowed:
            raise denied()
