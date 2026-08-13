from uuid import uuid4

import pytest

from app.core.errors import DomainError
from app.modules.auth.authorization import (
    AuthorizationPolicy,
    PolicyRequirement,
)
from app.modules.auth.session_service import AuthPrincipal


class ForbiddenForTest(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="TEST_FORBIDDEN",
            message="Access is forbidden.",
            status_code=403,
        )


class InvalidStateForTest(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="TEST_INVALID_STATE",
            message="State is invalid.",
            status_code=409,
        )


def principal(*, roles: tuple[str, ...], permissions: tuple[str, ...]) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="operator@example.test",
        roles=roles,
        account_type=None,
        permissions=permissions,
    )


def test_permission_grants_capability_without_matching_role() -> None:
    actor = principal(roles=("AUDITOR",), permissions=("dossier.review.assign",))

    AuthorizationPolicy.require_capability(
        actor,
        PolicyRequirement(
            permission="dossier.review.assign",
            compatible_roles=frozenset({"SUPER_ADMIN"}),
        ),
        ForbiddenForTest,
    )


def test_compatible_server_role_grants_capability_during_permission_migration() -> None:
    actor = principal(roles=("REVIEWER",), permissions=())

    AuthorizationPolicy.require_capability(
        actor,
        PolicyRequirement(
            permission="dossier.review.submit",
            compatible_roles=frozenset({"REVIEWER"}),
        ),
        ForbiddenForTest,
    )


def test_unlisted_role_and_permission_are_denied_by_default() -> None:
    actor = principal(roles=("APPLICANT",), permissions=())

    with pytest.raises(ForbiddenForTest):
        AuthorizationPolicy.require_capability(
            actor,
            PolicyRequirement(
                permission="admin.staff.manage",
                compatible_roles=frozenset({"SUPER_ADMIN"}),
            ),
            ForbiddenForTest,
        )


def test_capability_predicate_supports_resource_queries_without_exceptions() -> None:
    requirement = PolicyRequirement(
        permission="review.submit",
        compatible_roles=frozenset({"REVIEWER"}),
        allow_super_admin=False,
    )

    assert AuthorizationPolicy.allows_capability(
        principal(roles=("AUDITOR",), permissions=("review.submit",)), requirement
    )
    assert not AuthorizationPolicy.allows_capability(
        principal(roles=("APPLICANT",), permissions=()), requirement
    )


def test_super_admin_bypass_must_be_explicit() -> None:
    actor = principal(roles=("SUPER_ADMIN",), permissions=())
    requirement = PolicyRequirement(
        permission="admin.staff.manage",
        compatible_roles=frozenset(),
        allow_super_admin=False,
    )

    with pytest.raises(ForbiddenForTest):
        AuthorizationPolicy.require_capability(
            actor,
            requirement,
            ForbiddenForTest,
        )


def test_resource_scope_and_state_are_independent_mandatory_checks() -> None:
    with pytest.raises(ForbiddenForTest):
        AuthorizationPolicy.require_resource_scope(False, ForbiddenForTest)

    with pytest.raises(InvalidStateForTest):
        AuthorizationPolicy.require_business_state(False, InvalidStateForTest)

    AuthorizationPolicy.require_resource_scope(True, ForbiddenForTest)
    AuthorizationPolicy.require_business_state(True, InvalidStateForTest)
