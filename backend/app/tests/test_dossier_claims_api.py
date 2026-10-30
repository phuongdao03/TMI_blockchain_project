import asyncio
from dataclasses import replace
from uuid import UUID, uuid4

from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.types import DossierClaim, DossierView
from app.tests.test_dossier_api import StubDossierService, _principal, _request


class ClaimsService(StubDossierService):
    async def replace_claims(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        expected_revision: int,
        claims: tuple[DossierClaim, ...],
    ) -> DossierView:
        self._require_access()
        assert dossier_id == self.dossier_id
        return replace(
            self._view(), claims=claims, claims_revision=expected_revision + 1
        )


def test_claim_api_aliases_validation_and_authorization_envelope() -> None:
    principal = _principal()
    service = ClaimsService(principal)
    path = f"/api/v1/dossiers/{service.dossier_id}/claims"
    body = {
        "expectedRevision": 0,
        "claims": [
            {
                "id": str(uuid4()),
                "criterionKey": "origin",
                "statement": "The dated manuscript establishes provenance.",
                "evidenceMediaIds": [str(uuid4())],
            }
        ],
    }
    response = asyncio.run(_request("PUT", path, service, principal, json=body))
    assert response.status_code == 200
    assert response.json()["data"]["claimsRevision"] == 1
    assert response.json()["data"]["claims"] == body["claims"]
    service.forbidden = True
    assert (
        asyncio.run(_request("PUT", path, service, principal, json=body)).status_code
        == 403
    )
    body["expectedRevision"] = -1
    assert (
        asyncio.run(_request("PUT", path, service, principal, json=body)).status_code
        == 422
    )
