from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.schemas import (
    ErrorEnvelope,
    ListResponseMeta,
    PaginatedSuccessEnvelope,
    ResponseMeta,
    SuccessEnvelope,
)
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.blockchain.dependencies import BlockchainServiceDependency
from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    DocumentEvidenceStatus,
)
from app.modules.blockchain.schemas import (
    BlockchainQueuedData,
    BlockchainTransactionData,
    DocumentEvidenceData,
)

router = APIRouter(prefix="/api/v1/admin/blockchain", tags=["blockchain-admin"])

RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Blockchain access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Transaction not found.", "model": ErrorEnvelope},
    409: {"description": "Transaction state conflict.", "model": ErrorEnvelope},
    422: {"description": "Request is invalid.", "model": ErrorEnvelope},
    503: {"description": "Blockchain service unavailable.", "model": ErrorEnvelope},
}


@router.get(
    "/transactions",
    response_model=PaginatedSuccessEnvelope[list[BlockchainTransactionData]],
    responses=RESPONSES,
)
async def list_blockchain_transactions(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: BlockchainServiceDependency,
    transaction_status: Annotated[
        BlockchainTransactionStatus | None,
        Query(alias="status"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[BlockchainTransactionData]]:
    rows, total = await service.list_admin(
        principal,
        status=transaction_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[BlockchainTransactionData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/document-evidences",
    response_model=PaginatedSuccessEnvelope[list[DocumentEvidenceData]],
    responses=RESPONSES,
)
async def list_document_evidences(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: BlockchainServiceDependency,
    evidence_status: Annotated[
        DocumentEvidenceStatus | None,
        Query(alias="status"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedSuccessEnvelope[list[DocumentEvidenceData]]:
    rows, total = await service.list_document_evidences_admin(
        principal,
        status=evidence_status,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=[DocumentEvidenceData.model_validate(row) for row in rows],
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.post(
    "/transactions/{transaction_id}/retry",
    response_model=SuccessEnvelope[BlockchainTransactionData],
    responses=RESPONSES,
)
async def retry_blockchain_transaction(
    transaction_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: BlockchainServiceDependency,
) -> SuccessEnvelope[BlockchainTransactionData]:
    transaction = await service.retry_admin(principal, transaction_id)
    return SuccessEnvelope(
        data=BlockchainTransactionData.model_validate(transaction),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/reconcile",
    response_model=SuccessEnvelope[BlockchainQueuedData],
    responses=RESPONSES,
)
async def reconcile_blockchain_transactions(
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: BlockchainServiceDependency,
) -> SuccessEnvelope[BlockchainQueuedData]:
    await service.reconcile_admin(principal)
    return SuccessEnvelope(
        data=BlockchainQueuedData(),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
