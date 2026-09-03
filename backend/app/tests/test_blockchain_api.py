import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.admin_read_dependencies import (
    get_blockchain_admin_read_service,
)
from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    DocumentEvidenceStatus,
)
from app.modules.blockchain.proof_registry_dependencies import (
    get_thv_proof_registry_service,
)
from app.modules.blockchain.types import (
    BlockchainTransactionView,
    DocumentEvidenceView,
)

NOW = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)


class StubBlockchainService:
    def __init__(self) -> None:
        self.transaction_id = uuid4()
        self.reconcile_requested = False

    def view(self) -> BlockchainTransactionView:
        return BlockchainTransactionView(
            id=self.transaction_id,
            dossier_id=uuid4(),
            dossier_version_id=uuid4(),
            certificate_id=None,
            network="local",
            chain_id=31_337,
            contract_address="0x" + "12" * 20,
            method="issueCertificate",
            payload_hash="ab" * 32,
            tx_hash=None,
            nonce=None,
            status=BlockchainTransactionStatus.FAILED,
            confirmations=0,
            error_code="RPC_FAILURE",
            error_message="RPC unavailable",
            broadcast_at=None,
            confirmed_at=None,
            created_at=NOW,
            updated_at=NOW,
        )

    async def list_transactions(
        self,
        principal: AuthPrincipal,
        *,
        status: BlockchainTransactionStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[BlockchainTransactionView, ...], int]:
        del principal, status, page, page_size
        return (self.view(),), 1

    async def reconcile_pending(self) -> None:
        self.reconcile_requested = True

    async def list_document_evidences(
        self,
        principal: AuthPrincipal,
        *,
        status: DocumentEvidenceStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[DocumentEvidenceView, ...], int]:
        del principal, status, page, page_size
        return (
            (
                DocumentEvidenceView(
                    id=uuid4(),
                    document_hash_claim_id=uuid4(),
                    dossier_id=uuid4(),
                    dossier_version_id=uuid4(),
                    evidence_key="12" * 32,
                    commitment="34" * 32,
                    version_no=1,
                    previous_evidence_key=None,
                    recorded_at=NOW,
                    status=DocumentEvidenceStatus.CONFIRMED,
                    transaction_id=self.transaction_id,
                    network="local",
                    tx_hash="0x" + "56" * 32,
                    confirmations=2,
                    error_code=None,
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ),
            1,
        )


async def _request(
    method: str,
    path: str,
    service: StubBlockchainService,
) -> httpx.Response:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="chain-admin@tmigroup.vn",
        roles=("SUPER_ADMIN",),
        permissions=("blockchain.manage",),
    )
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_blockchain_admin_read_service] = lambda: service
    app.dependency_overrides[get_thv_proof_registry_service] = lambda: service
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path)


def test_blockchain_admin_list_retry_and_reconcile_contracts() -> None:
    service = StubBlockchainService()
    listed = asyncio.run(
        _request("GET", "/api/v1/admin/blockchain/transactions", service)
    )
    retried = asyncio.run(
        _request(
            "POST",
            (f"/api/v1/admin/blockchain/transactions/{service.transaction_id}/retry"),
            service,
        )
    )
    reconciled = asyncio.run(
        _request("POST", "/api/v1/admin/blockchain/reconcile", service)
    )
    document_evidences = asyncio.run(
        _request("GET", "/api/v1/admin/blockchain/document-evidences", service)
    )

    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] == 1
    assert retried.status_code == 410
    assert reconciled.status_code == 200
    assert reconciled.json()["data"]["status"] == "queued"
    assert service.reconcile_requested is True
    assert document_evidences.status_code == 200
    assert document_evidences.json()["data"][0]["status"] == "EVIDENCE_CONFIRMED"
    assert "submitterReference" not in document_evidences.text
