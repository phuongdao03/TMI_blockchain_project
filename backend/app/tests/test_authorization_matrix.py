from collections.abc import Callable
from uuid import uuid4

import pytest

from app.api.v1.audit import require_audit_access
from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.certificates.service import CertificateService
from app.modules.cms.service import CmsService
from app.modules.council.service import (
    MEMBER_ROLES,
    SECRETARY_ROLES,
    CouncilService,
)
from app.modules.dossiers.service import DossierService
from app.modules.operations.service import OPERATIONS_ROLES
from app.modules.payments.service import FINANCE_ROLES, PAYMENT_ROLES, PaymentService
from app.modules.reviews.service import ReviewService


def _principal(role: str, *permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email=f"{role.lower()}@tmigroup.vn",
        roles=(role,),
        permissions=permissions,
    )


ROLE_GUARDS: tuple[tuple[str, Callable[[AuthPrincipal], None], str, str, str], ...] = (
    (
        "dossier mutation",
        DossierService._require_mutation_role,
        "USER",
        "MODERATOR",
        "dossier.manage",
    ),
    (
        "review assignment",
        ReviewService._require_admin,
        "SUPER_ADMIN",
        "MODERATOR",
        "review.assign",
    ),
    (
        "review scoring",
        ReviewService._require_reviewer,
        "MODERATOR",
        "USER",
        "review.submit",
    ),
    (
        "council administration",
        CouncilService._require_secretary,
        "SUPER_ADMIN",
        "MODERATOR",
        "council.manage",
    ),
    (
        "council voting",
        CouncilService._require_member,
        "SUPER_ADMIN",
        "MODERATOR",
        "council.vote",
    ),
    (
        "blockchain administration",
        BlockchainTransactionService._require_admin,
        "SUPER_ADMIN",
        "MODERATOR",
        "blockchain.manage",
    ),
    (
        "CMS administration",
        CmsService._require_admin,
        "SUPER_ADMIN",
        "USER",
        "cms.manage",
    ),
    (
        "certificate access",
        CertificateService._require_role,
        "USER",
        "MODERATOR",
        "certificate.read",
    ),
    (
        "audit access",
        require_audit_access,
        "SUPER_ADMIN",
        "MODERATOR",
        "audit.read",
    ),
)


@pytest.mark.parametrize(
    ("resource", "guard", "allowed_role", "denied_role", "permission"),
    ROLE_GUARDS,
    ids=[case[0] for case in ROLE_GUARDS],
)
def test_critical_role_guards_default_deny(
    resource: str,
    guard: Callable[[AuthPrincipal], None],
    allowed_role: str,
    denied_role: str,
    permission: str,
) -> None:
    del resource
    guard(_principal(allowed_role))
    with pytest.raises(DomainError):
        guard(_principal(denied_role))
    guard(_principal(denied_role, permission))


@pytest.mark.parametrize(
    ("allowed", "denied", "permission"),
    (
        (PAYMENT_ROLES, "MODERATOR", "payment.create"),
        (FINANCE_ROLES, "USER", "payment.manage"),
    ),
)
def test_payment_role_scopes_default_deny(
    allowed: frozenset[str], denied: str, permission: str
) -> None:
    PaymentService._require_role(_principal(next(iter(allowed))), allowed)
    with pytest.raises(DomainError):
        PaymentService._require_role(_principal(denied), allowed)
    PaymentService._require_role(_principal(denied, permission), allowed)


def test_operations_role_scope_excludes_business_users() -> None:
    assert OPERATIONS_ROLES == frozenset({"SUPER_ADMIN"})
    assert OPERATIONS_ROLES.isdisjoint({"VIEWER", "USER", "MODERATOR"})


def test_council_role_scopes_are_limited_to_super_admin() -> None:
    assert SECRETARY_ROLES == frozenset({"SUPER_ADMIN"})
    assert MEMBER_ROLES == frozenset({"SUPER_ADMIN"})
