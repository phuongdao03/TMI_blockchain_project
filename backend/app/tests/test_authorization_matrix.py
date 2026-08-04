from collections.abc import Callable
from uuid import uuid4

import pytest

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.cms.service import CmsService
from app.modules.council.service import CouncilService
from app.modules.dossiers.service import DossierService
from app.modules.operations.service import OPERATIONS_ROLES
from app.modules.payments.service import FINANCE_ROLES, PAYMENT_ROLES, PaymentService
from app.modules.reviews.service import ReviewService


def _principal(role: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email=f"{role.lower()}@tmigroup.vn",
        roles=(role,),
    )


ROLE_GUARDS: tuple[tuple[str, Callable[[AuthPrincipal], None], str, str], ...] = (
    (
        "dossier mutation",
        DossierService._require_mutation_role,
        "APPLICANT",
        "REVIEWER",
    ),
    (
        "review assignment",
        ReviewService._require_admin,
        "SUPER_ADMIN",
        "REVIEWER",
    ),
    (
        "review scoring",
        ReviewService._require_reviewer,
        "REVIEWER",
        "APPLICANT",
    ),
    (
        "council administration",
        CouncilService._require_secretary,
        "COUNCIL_SECRETARY",
        "COUNCIL_MEMBER",
    ),
    (
        "council voting",
        CouncilService._require_member,
        "COUNCIL_MEMBER",
        "COUNCIL_SECRETARY",
    ),
    (
        "blockchain administration",
        BlockchainTransactionService._require_admin,
        "BLOCKCHAIN_ADMIN",
        "FINANCE_ADMIN",
    ),
    (
        "CMS administration",
        CmsService._require_admin,
        "CONTENT_ADMIN",
        "APPLICANT",
    ),
)


@pytest.mark.parametrize(
    ("resource", "guard", "allowed_role", "denied_role"),
    ROLE_GUARDS,
    ids=[case[0] for case in ROLE_GUARDS],
)
def test_critical_role_guards_default_deny(
    resource: str,
    guard: Callable[[AuthPrincipal], None],
    allowed_role: str,
    denied_role: str,
) -> None:
    del resource
    guard(_principal(allowed_role))
    with pytest.raises(DomainError):
        guard(_principal(denied_role))


@pytest.mark.parametrize(
    ("allowed", "denied"),
    ((PAYMENT_ROLES, "REVIEWER"), (FINANCE_ROLES, "APPLICANT")),
)
def test_payment_role_scopes_default_deny(allowed: frozenset[str], denied: str) -> None:
    PaymentService._require_role(_principal(next(iter(allowed))), allowed)
    with pytest.raises(DomainError):
        PaymentService._require_role(_principal(denied), allowed)


def test_operations_role_scope_excludes_business_users() -> None:
    assert OPERATIONS_ROLES == frozenset(
        {"FINANCE_ADMIN", "BLOCKCHAIN_ADMIN", "SUPER_ADMIN"}
    )
    assert OPERATIONS_ROLES.isdisjoint({"APPLICANT", "REVIEWER", "CONTENT_ADMIN"})
