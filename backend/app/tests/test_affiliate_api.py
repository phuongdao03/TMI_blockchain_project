import asyncio
from uuid import uuid4

import httpx
from fastapi import FastAPI

from app.api.v1.affiliate import admin_router, router
from app.core.config import Settings, get_settings
from app.core.middleware import RequestContextMiddleware
from app.main import create_application as _create_application  # noqa: F401
from app.modules.affiliate.dependencies import get_affiliate_service
from app.modules.affiliate.service import AffiliateService
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.tests.test_affiliate_service import _assign_role, _seed_rule_set
from app.tests.test_payment_service import ADMIN_ID, _service


def test_affiliate_api_exposes_real_dashboard_attribution_and_admin_rules() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        owner_principal = owner
        principal = [owner_principal]
        settings = Settings.model_validate(
            {
                "app_env": "local",
                "app_base_url": "https://tinhhoaviet.example",
                "affiliate_enabled": True,
            }
        )
        try:
            async with sessions() as session:
                await _assign_role(session, owner.user_id, "USER")
                await _seed_rule_set(session)
                referred_id = uuid4()
                session.add(
                    User(
                        id=referred_id,
                        email="api-referral@example.vn",
                        status=UserStatus.ACTIVE,
                    )
                )
                await session.flush()
                await _assign_role(session, referred_id, "USER")
                await session.commit()

            affiliate_session = sessions()
            affiliate_service = AffiliateService(
                affiliate_session,
                affiliate_enabled=True,
            )
            app = FastAPI()
            app.add_middleware(RequestContextMiddleware)
            app.include_router(router)
            app.include_router(admin_router)
            app.dependency_overrides[get_affiliate_service] = lambda: affiliate_service
            app.dependency_overrides[get_current_principal] = lambda: principal[0]
            app.dependency_overrides[get_csrf_protected_principal] = lambda: principal[
                0
            ]
            app.dependency_overrides[get_settings] = lambda: settings

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                dashboard = await client.get("/api/v1/affiliate/me")
                assert dashboard.status_code == 200
                data = dashboard.json()["data"]
                assert data["referralCode"].startswith("THV")
                assert data["referralUrl"].startswith(
                    "https://tinhhoaviet.example/?ref="
                )
                assert data["availableBalanceMinor"] == 0
                assert data["reservedBalanceMinor"] == 0
                assert dashboard.headers["cache-control"] == "no-store"

                click_id = uuid4()
                click = await client.post(
                    "/api/v1/affiliate/referral-clicks",
                    json={
                        "referralCode": data["referralCode"],
                        "eventId": str(click_id),
                    },
                )
                assert click.status_code == 201

                principal[0] = AuthPrincipal(
                    user_id=referred_id,
                    session_id=uuid4(),
                    email="api-referral@example.vn",
                    roles=("USER",),
                )
                claimed = await client.post(
                    "/api/v1/affiliate/referrals/claim",
                    json={
                        "referralCode": data["referralCode"],
                        "clickId": str(click_id),
                    },
                )
                assert claimed.status_code == 200
                assert claimed.json()["data"]["affiliateUserId"] == str(owner.user_id)

                principal[0] = owner_principal
                referrals = await client.get(
                    "/api/v1/affiliate/me/referrals?limit=50&offset=0"
                )
                assert referrals.status_code == 200
                assert len(referrals.json()["data"]) == 1
                assert "referredUserId" not in referrals.json()["data"][0]
                assert referrals.json()["data"][0]["conversionCount"] == 0

                own_commissions = await client.get("/api/v1/affiliate/me/commissions")
                assert own_commissions.status_code == 200
                assert own_commissions.json()["data"] == []

                principal[0] = AuthPrincipal(
                    user_id=ADMIN_ID,
                    session_id=uuid4(),
                    email="admin@example.vn",
                    roles=("SUPER_ADMIN",),
                )
                profiles = await client.get("/api/v1/admin/affiliate/profiles")
                assert profiles.status_code == 200
                profile_rows = profiles.json()["data"]
                assert {row["userId"] for row in profile_rows} == {
                    str(owner.user_id),
                    str(referred_id),
                }
                assert all("email" not in row for row in profile_rows)
                profile_referrals = await client.get(
                    f"/api/v1/admin/affiliate/profiles/{owner.user_id}/referrals"
                )
                assert profile_referrals.status_code == 200
                assert len(profile_referrals.json()["data"]) == 1
                assert "referredUserId" not in profile_referrals.json()["data"][0]
                suspended = await client.post(
                    f"/api/v1/admin/affiliate/profiles/{owner.user_id}/suspend",
                    json={"reason": "Manual review found suspicious activity."},
                )
                assert suspended.status_code == 200
                assert suspended.json()["data"]["status"] == "SUSPENDED"
                restored = await client.post(
                    f"/api/v1/admin/affiliate/profiles/{owner.user_id}/restore",
                    json={"reason": "Review completed; access restored."},
                )
                assert restored.status_code == 200
                assert restored.json()["data"]["status"] == "ACTIVE"
                rule_rows = await client.get("/api/v1/admin/affiliate/commission-rules")
                assert rule_rows.status_code == 200
                assert rule_rows.json()["data"][0]["enabled"] is False
                admin_commissions = await client.get(
                    "/api/v1/admin/affiliate/commissions"
                )
                assert admin_commissions.status_code == 200
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
