import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from app.api.v1.supplements import get_supplement_service
from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.supplements.schemas import SupplementData
from app.tests.test_dossier_api import _principal


def test_supplement_contract_validates_version_and_hides_internal_actor_fields() -> (
    None
):
    async def exercise() -> None:
        dossier_id, version_id = uuid4(), uuid4()

        class Stub:
            async def create(self, principal, requested_dossier, **payload):
                assert requested_dossier == dossier_id
                assert payload["expected_version_id"] == version_id
                return SupplementData(
                    id=uuid4(),
                    dossier_id=dossier_id,
                    requested_version_id=version_id,
                    criterion_key=payload["criterion_key"],
                    criterion_label="Nguồn gốc",
                    claim_id=None,
                    requested_information=payload["requested_information"],
                    reason=payload["reason"],
                    priority="NORMAL",
                    due_at=None,
                    created_at=datetime.now(UTC),
                    status="OPEN",
                    revision=0,
                    responses=(),
                )

        app = create_application(
            settings=Settings.model_validate({"app_env": "local"}),
            health_service=HealthService({}),
        )
        app.dependency_overrides[get_supplement_service] = lambda: Stub()
        app.dependency_overrides[get_current_principal] = _principal
        app.dependency_overrides[get_csrf_protected_principal] = _principal
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client,
        ):
            path = f"/api/v1/dossiers/{dossier_id}/supplement-requests"
            body = {
                "expectedVersionId": str(version_id),
                "criterionKey": "origin",
                "requestedInformation": "Please provide a dated archive source.",
                "reason": "The chronology is not yet supported.",
            }
            response = await client.post(path, json=body)
            assert response.status_code == 201
            data = response.json()["data"]
            assert data["criterionLabel"] == "Nguồn gốc" and data["revision"] == 0
            assert "createdBy" not in data and "authorId" not in data
            del body["expectedVersionId"]
            assert (await client.post(path, json=body)).status_code == 422

    asyncio.run(exercise())
