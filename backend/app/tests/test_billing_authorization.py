from uuid import uuid4

import pytest

from app.api.v1.billing import BillingForbiddenError, _require, _require_any
from app.modules.auth.session_service import AuthPrincipal


def _principal(*permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="operator@example.test",
        roles=("ADMIN",),
        permissions=permissions,
    )


def test_fee_admin_routes_require_the_requested_capability() -> None:
    _require(_principal("billing.fees.read"), "billing.fees.read")
    _require_any(
        _principal("billing.fees.policies.approve"),
        ("billing.fees.read", "billing.fees.policies.approve"),
    )
    with pytest.raises(BillingForbiddenError):
        _require(_principal("payments.read"), "billing.fees.policies.approve")
