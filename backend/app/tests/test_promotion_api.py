import asyncio
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import main as application_models  # noqa: F401
from app.api.v1.admin_promotions import router as admin_router
from app.api.v1.promotion_distribution import router as distribution_router
from app.core.errors import install_exception_handlers
from app.db.base import Base
from app.db.session import get_session
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.promotions.distribution import PromotionDistributionService


def test_admin_api_create_preview_publish_distribute_and_report(monkeypatch):
    async def no_background_job(job_id):
        pass

    monkeypatch.setattr(
        "app.api.v1.promotion_distribution.drain_distribution_job", no_background_job
    )

    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        admin, user = uuid4(), uuid4()
        async with factory() as session:
            role = Role(id=uuid4(), code="USER")
            session.add_all(
                [
                    role,
                    User(id=admin, email="admin@example.vn", status=UserStatus.ACTIVE),
                    User(
                        id=user, email="customer@example.vn", status=UserStatus.ACTIVE
                    ),
                ]
            )
            await session.flush()
            session.add(UserRole(user_id=user, role_id=role.id))
            await session.commit()
        principal = AuthPrincipal(
            user_id=admin,
            session_id=uuid4(),
            email="admin@example.vn",
            roles=("SUPER_ADMIN",),
        )
        app = FastAPI()
        app.include_router(admin_router)
        app.include_router(distribution_router)
        install_exception_handlers(app)

        @app.middleware("http")
        async def request_id(request: Request, call_next):
            request.state.request_id = "promotion-api-test"
            return await call_next(request)

        async def session_override():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_current_principal] = lambda: principal
        app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
        app.dependency_overrides[get_session] = session_override
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = {
                "code": "API_GIFT",
                "name": "Test gift",
                "title": "Thank you",
                "description": "A gift",
                "terms": "Service discount",
                "programType": "MANUAL",
                "policy": {"budgetVnd": 1000000},
            }
            response = await client.post("/api/v1/admin/promotions", json=payload)
            assert response.status_code == 200, response.text
            campaign = response.json()["data"]
            identifier = campaign["id"]
            assert (
                campaign["status"] == "DRAFT"
                and campaign["policy"]["budgetVnd"] == 1000000
            )
            preview = (
                await client.post(
                    f"/api/v1/admin/promotions/{identifier}/audience-preview", json={}
                )
            ).json()["data"]
            assert preview["eligibleCount"] == 1
            search = (
                await client.get(
                    f"/api/v1/admin/promotions/{identifier}/recipient-search",
                    params={"q": "customer@"},
                )
            ).json()["data"]
            assert (
                search["items"][0]["id"] == str(user) and search["items"][0]["eligible"]
            )
            csv_response = await client.get("/api/v1/admin/promotions/analytics.csv")
            assert csv_response.status_code == 200 and "orderId" in csv_response.text

            published = await client.post(
                f"/api/v1/admin/promotions/{identifier}/publish"
            )
            assert published.json()["data"]["status"] == "ACTIVE"
            issued = await client.post(
                f"/api/v1/admin/promotions/{identifier}/issue",
                json={
                    "reason": "Test audience issuance",
                    "idempotencyKey": "integration-issue-1",
                    "previewToken": preview["previewToken"],
                },
            )
            assert issued.status_code == 200, issued.text
            async with factory() as session:
                await PromotionDistributionService(session).run_batch(
                    __import__("uuid").UUID(issued.json()["data"]["id"])
                )
            stats = (
                await client.get(f"/api/v1/admin/promotions/{identifier}/stats")
            ).json()["data"]
            assert (
                stats["issuedCount"] == 1
                and stats["discountVnd"] == 0
                and stats["issuedValueVnd"] == 200000
            )
            audit = (await client.get("/api/v1/admin/promotions/audit")).json()["data"]
            assert audit["total"] >= 3
            principal = AuthPrincipal(
                user_id=user,
                session_id=uuid4(),
                email="customer@example.vn",
                roles=("USER",),
            )
            assert (await client.get("/api/v1/admin/promotions")).status_code == 403
        await engine.dispose()

    asyncio.run(scenario())
