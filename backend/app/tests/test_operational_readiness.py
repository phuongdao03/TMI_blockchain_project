import asyncio

import httpx
from fastapi import FastAPI

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application


class UnavailableDatabaseProbe:
    async def check(self) -> bool:
        raise OSError("postgresql://user:do-not-expose@private-db.example/tmi")

    async def close(self) -> None:
        return None


def test_database_outage_blocks_readiness_without_leaking_connection_details() -> None:
    async def exercise() -> None:
        app: FastAPI = create_application(
            settings=Settings.model_validate({"app_env": "local"}),
            health_service=HealthService({"database": UnavailableDatabaseProbe()}),
        )
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.get("/ready")

        assert response.status_code == 503
        payload = response.json()
        assert payload["error"]["code"] == "SERVICE_NOT_READY"
        assert payload["error"]["details"] == {"dependencies": {"database": "down"}}
        assert "do-not-expose" not in response.text
        assert "private-db.example" not in response.text

    asyncio.run(exercise())
