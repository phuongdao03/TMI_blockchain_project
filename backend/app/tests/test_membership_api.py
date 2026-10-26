import asyncio

import httpx
from sqlalchemy import select

from app.core.health import HealthService
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.memberships.models import MembershipPlan
from app.modules.wallet.service import WalletLedger
from app.tests.test_payment_service import ADMIN_ID, _service


def test_public_plans_and_admin_diamond_application_workflow() -> None:
    async def exercise() -> None:
        payment, _, engine, owner = await _service()
        current = [owner]
        app = create_application(health_service=HealthService({}))
        app.dependency_overrides[get_csrf_protected_principal] = lambda: current[0]

        async def test_session():
            yield payment._session

        app.dependency_overrides[get_session] = test_session
        try:
            async with (
                app.router.lifespan_context(app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://testserver",
                ) as client,
            ):
                async with payment._session.begin():
                    payment._session.add_all(
                        [
                            MembershipPlan(
                                name="Kết nối",
                                tier="SILVER",
                                amount_minor=490_000,
                                duration_days=365,
                            ),
                            MembershipPlan(
                                name="Tinh hoa",
                                tier="PRESTIGE",
                                amount_minor=3_990_000,
                                duration_days=365,
                            ),
                        ]
                    )

                catalog = await client.get("/api/v1/memberships/plans")
                assert catalog.status_code == 200
                assert [plan["tier"] for plan in catalog.json()["data"]["plans"]] == [
                    "SILVER",
                    "PRESTIGE",
                ]
                assert any(
                    "nội dung công khai" in benefit
                    for benefit in catalog.json()["data"]["member"]["benefits"]
                )

                async with payment._session.begin():
                    silver_id = await payment._session.scalar(
                        select(MembershipPlan.id).where(MembershipPlan.tier == "SILVER")
                    )
                    await WalletLedger(payment._session).post(
                        user_id=owner.user_id,
                        delta=5_000_000,
                        kind="TOPUP",
                        key="api-membership-funds",
                        reference="topup:api-membership-test",
                        description="Test funding",
                    )
                assert silver_id is not None
                current[0] = owner
                app.dependency_overrides[get_current_principal] = lambda: current[0]
                quote = await client.post(
                    f"/api/v1/memberships/plans/{silver_id}/quote",
                    json={"renewalOptIn": False},
                )
                assert quote.status_code == 200
                expected_amount = quote.json()["data"]["amountDueMinor"]
                purchase_url = f"/api/v1/memberships/plans/{silver_id}/purchases"
                wrong_amount = await client.post(
                    purchase_url,
                    json={"expectedAmountMinor": expected_amount - 1},
                    headers={"Idempotency-Key": "api-silver-wrong-amount"},
                )
                assert wrong_amount.status_code == 409
                purchased = await client.post(
                    purchase_url,
                    json={"expectedAmountMinor": expected_amount},
                    headers={"Idempotency-Key": "api-silver-confirmed"},
                )
                assert purchased.status_code == 200
                assert purchased.json()["data"]["tier"] == "SILVER"

                submitted = await client.post(
                    "/api/v1/memberships/diamond-applications",
                    json={"statement": "I want to join the Diamond community."},
                )
                assert submitted.status_code == 200
                application_id = submitted.json()["data"]["id"]
                assert submitted.json()["data"]["status"] == "PENDING"

                denied = await client.get(
                    "/api/v1/admin/memberships/diamond-applications"
                )
                assert denied.status_code == 403

                current[0] = AuthPrincipal(
                    user_id=ADMIN_ID,
                    session_id=owner.session_id,
                    email="admin@example.vn",
                    roles=("SUPER_ADMIN",),
                )
                admin_membership = await client.get("/api/v1/memberships/me")
                assert admin_membership.status_code == 403
                admin_quote = await client.post(
                    f"/api/v1/memberships/plans/{silver_id}/quote",
                    json={"renewalOptIn": False},
                )
                assert admin_quote.status_code == 403
                admin_purchase = await client.post(
                    purchase_url,
                    json={"expectedAmountMinor": expected_amount},
                    headers={"Idempotency-Key": "admin-membership-purchase"},
                )
                assert admin_purchase.status_code == 403
                admin_application = await client.post(
                    "/api/v1/memberships/diamond-applications",
                    json={"statement": "Admin account application attempt."},
                )
                assert admin_application.status_code == 403
                listed = await client.get(
                    "/api/v1/admin/memberships/diamond-applications"
                )
                assert listed.status_code == 200
                assert listed.json()["data"]["applications"][0]["id"] == application_id
                requested_info = await client.post(
                    f"/api/v1/admin/memberships/diamond-applications/"
                    f"{application_id}/request-info",
                    json={"note": "Please add more information."},
                )
                assert requested_info.status_code == 200
                assert requested_info.json()["data"]["status"] == "INFO_REQUESTED"

                current[0] = owner
                resubmitted = await client.post(
                    "/api/v1/memberships/diamond-applications",
                    json={"statement": "Here is the requested additional information."},
                )
                assert resubmitted.status_code == 200
                assert resubmitted.json()["data"]["id"] == application_id
                assert resubmitted.json()["data"]["status"] == "PENDING"

                current[0] = AuthPrincipal(
                    user_id=ADMIN_ID,
                    session_id=owner.session_id,
                    email="admin@example.vn",
                    roles=("SUPER_ADMIN",),
                )
                rejected = await client.post(
                    f"/api/v1/admin/memberships/diamond-applications/"
                    f"{application_id}/reject",
                    json={"note": "Application does not meet criteria."},
                )
                assert rejected.status_code == 200
                assert rejected.json()["data"]["status"] == "REJECTED"

                current[0] = owner
                replacement = await client.post(
                    "/api/v1/memberships/diamond-applications",
                    json={"statement": "Submitting a revised application."},
                )
                assert replacement.status_code == 200
                replacement_id = replacement.json()["data"]["id"]
                current[0] = AuthPrincipal(
                    user_id=ADMIN_ID,
                    session_id=owner.session_id,
                    email="admin@example.vn",
                    roles=("SUPER_ADMIN",),
                )
                approved = await client.post(
                    f"/api/v1/admin/memberships/diamond-applications/"
                    f"{replacement_id}/approve",
                    json={"note": "Approved for membership purchase."},
                )
                assert approved.status_code == 200
                assert approved.json()["data"]["status"] == "APPROVED"
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
