"""Authenticated runtime API for the optional THVProofRegistry contract."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.blockchain.proof_registry_dependencies import (
    THVProofRegistryServiceDependency,
)
from app.modules.blockchain.schemas import (
    THVProofRegistryIntentData,
    THVProofRegistryIntentRequest,
    THVProofRegistryProofData,
    THVProofRegistryQueueItemData,
    THVProofRegistryStatusData,
    THVProofRegistrySubmissionRequest,
    THVProofRegistryVerificationData,
)

router = APIRouter(
    prefix="/api/v1/blockchain/proof-registry",
    tags=["thv-proof-registry"],
)
RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Blockchain signing is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Dossier was not found.", "model": ErrorEnvelope},
    409: {"description": "Proof registry state conflict.", "model": ErrorEnvelope},
    422: {"description": "Request is invalid.", "model": ErrorEnvelope},
    503: {"description": "Proof registry is unavailable.", "model": ErrorEnvelope},
}


def _success(request: Request, data: object) -> SuccessEnvelope[object]:
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/signing-queue",
    response_model=SuccessEnvelope[list[THVProofRegistryQueueItemData]],
    responses=RESPONSES,
)
async def signing_queue(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: THVProofRegistryServiceDependency,
) -> SuccessEnvelope[list[THVProofRegistryQueueItemData]]:
    views = await service.signing_queue(principal)
    data = [THVProofRegistryQueueItemData.model_validate(view) for view in views]
    return _success(request, data)  # type: ignore[return-value]


@router.post(
    "/dossiers/{dossier_id}/versions/{version_no}/intents",
    response_model=SuccessEnvelope[THVProofRegistryIntentData],
    responses=RESPONSES,
)
async def prepare_record_proof_intent(
    dossier_id: UUID,
    version_no: int,
    body: THVProofRegistryIntentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: THVProofRegistryServiceDependency,
) -> SuccessEnvelope[THVProofRegistryIntentData]:
    view = await service.prepare_record_proof_intent(
        principal,
        dossier_id=dossier_id,
        version_no=version_no,
        connected_wallet=body.connected_wallet,
    )
    return _success(request, THVProofRegistryIntentData.model_validate(view))  # type: ignore[return-value]


@router.post(
    "/transactions/{transaction_id}/submissions",
    response_model=SuccessEnvelope[THVProofRegistryStatusData],
    responses=RESPONSES,
)
async def submit_record_proof_transaction(
    transaction_id: UUID,
    body: THVProofRegistrySubmissionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: THVProofRegistryServiceDependency,
) -> SuccessEnvelope[THVProofRegistryStatusData]:
    view = await service.submit_transaction(
        principal,
        transaction_id=transaction_id,
        intent_id=body.intent_id,
        transaction_hash=body.transaction_hash,
        connected_wallet=body.connected_wallet,
    )
    return _success(request, THVProofRegistryStatusData.model_validate(view))  # type: ignore[return-value]


@router.get(
    "/transactions/{transaction_id}/status",
    response_model=SuccessEnvelope[THVProofRegistryStatusData],
    responses=RESPONSES,
)
async def record_proof_transaction_status(
    transaction_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: THVProofRegistryServiceDependency,
) -> SuccessEnvelope[THVProofRegistryStatusData]:
    view = await service.transaction_status(
        principal,
        transaction_id=transaction_id,
        reconcile=True,
    )
    return _success(request, THVProofRegistryStatusData.model_validate(view))  # type: ignore[return-value]


@router.get(
    "/proofs/{asset_id}/versions/{version_no}",
    response_model=SuccessEnvelope[THVProofRegistryProofData],
    responses=RESPONSES,
)
async def get_proof(
    asset_id: str,
    version_no: int,
    request: Request,
    _: CurrentPrincipalDependency,
    service: THVProofRegistryServiceDependency,
) -> SuccessEnvelope[THVProofRegistryProofData]:
    view = await service.get_proof(asset_id=asset_id, version=version_no)
    return _success(request, THVProofRegistryProofData.model_validate(view))  # type: ignore[return-value]


@router.get(
    "/proofs/{asset_id}/versions/{version_no}/verify",
    response_model=SuccessEnvelope[THVProofRegistryVerificationData],
    responses=RESPONSES,
)
async def verify_proof(
    asset_id: str,
    version_no: int,
    expected_hash: Annotated[
        str,
        Query(alias="expectedHash", pattern=r"^0x[0-9a-fA-F]{64}$"),
    ],
    request: Request,
    _: CurrentPrincipalDependency,
    service: THVProofRegistryServiceDependency,
) -> SuccessEnvelope[THVProofRegistryVerificationData]:
    view = await service.verify_proof(
        asset_id=asset_id,
        version=version_no,
        expected_hash=expected_hash,
    )
    return _success(
        request,
        THVProofRegistryVerificationData.model_validate(view),
    )  # type: ignore[return-value]
