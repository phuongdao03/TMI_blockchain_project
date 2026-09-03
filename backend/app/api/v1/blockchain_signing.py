from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.blockchain.errors import BlockchainLegacyFlowDeprecatedError
from app.modules.blockchain.schemas import (
    SigningContextData,
    SigningIntentData,
    SigningIntentRequest,
    SigningQueueItemData,
    SigningStatusData,
    SigningSubmissionRequest,
    WalletChallengeData,
    WalletChallengeRequest,
    WalletLinkData,
    WalletLinkVerificationRequest,
)
from app.modules.blockchain.wallet_link_dependencies import WalletLinkServiceDependency

router = APIRouter(prefix="/api/v1/blockchain", tags=["blockchain-signing"])
RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Blockchain signing is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Blockchain resource was not found.", "model": ErrorEnvelope},
    409: {"description": "Blockchain signing conflict.", "model": ErrorEnvelope},
    410: {"description": "Legacy signing flow is deprecated.", "model": ErrorEnvelope},
    422: {"description": "Request is invalid.", "model": ErrorEnvelope},
    503: {"description": "Blockchain service unavailable.", "model": ErrorEnvelope},
}


def _success(request: Request, data: object) -> SuccessEnvelope[object]:
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/wallet-challenges",
    response_model=SuccessEnvelope[WalletChallengeData],
    responses=RESPONSES,
)
async def create_wallet_challenge(
    body: WalletChallengeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: WalletLinkServiceDependency,
) -> SuccessEnvelope[WalletChallengeData]:
    view = await service.create_wallet_challenge(
        principal,
        wallet_address=body.wallet_address,
        chain_id=body.chain_id,
    )
    return _success(request, WalletChallengeData.model_validate(view))  # type: ignore[return-value]


@router.post(
    "/wallet-links", response_model=SuccessEnvelope[WalletLinkData], responses=RESPONSES
)
async def verify_wallet_link(
    body: WalletLinkVerificationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: WalletLinkServiceDependency,
) -> SuccessEnvelope[WalletLinkData]:
    view = await service.verify_wallet_link(
        principal,
        challenge_id=body.challenge_id,
        nonce=body.nonce,
        signature=body.signature,
    )
    return _success(request, WalletLinkData.model_validate(view))  # type: ignore[return-value]


@router.get(
    "/wallet",
    response_model=SuccessEnvelope[WalletLinkData | None],
    responses=RESPONSES,
)
async def current_wallet(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: WalletLinkServiceDependency,
) -> SuccessEnvelope[WalletLinkData | None]:
    view = await service.current_wallet(principal)
    return _success(request, WalletLinkData.model_validate(view) if view else None)  # type: ignore[return-value]


@router.delete(
    "/wallet", response_model=SuccessEnvelope[WalletLinkData], responses=RESPONSES
)
async def revoke_current_wallet(
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: WalletLinkServiceDependency,
) -> SuccessEnvelope[WalletLinkData]:
    view = await service.revoke_current_wallet(principal)
    return _success(request, WalletLinkData.model_validate(view))  # type: ignore[return-value]


@router.get(
    "/signing-queue",
    response_model=SuccessEnvelope[list[SigningQueueItemData]],
    responses=RESPONSES,
)
async def list_signing_queue(
    request: Request,
    principal: CurrentPrincipalDependency,
) -> SuccessEnvelope[list[SigningQueueItemData]]:
    del request, principal
    raise BlockchainLegacyFlowDeprecatedError()


@router.get(
    "/transactions/{transaction_id}/signing-context",
    response_model=SuccessEnvelope[SigningContextData],
    responses=RESPONSES,
)
async def signing_context(
    transaction_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
) -> SuccessEnvelope[SigningContextData]:
    del transaction_id, request, principal
    raise BlockchainLegacyFlowDeprecatedError()


@router.post(
    "/transactions/{transaction_id}/intents",
    response_model=SuccessEnvelope[SigningIntentData],
    responses=RESPONSES,
)
async def prepare_signing_intent(
    transaction_id: UUID,
    body: SigningIntentRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
) -> SuccessEnvelope[SigningIntentData]:
    del transaction_id, body, request, principal
    raise BlockchainLegacyFlowDeprecatedError()


@router.post(
    "/transactions/{transaction_id}/submissions",
    response_model=SuccessEnvelope[SigningStatusData],
    responses=RESPONSES,
)
async def submit_signing_transaction(
    transaction_id: UUID,
    body: SigningSubmissionRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
) -> SuccessEnvelope[SigningStatusData]:
    del transaction_id, body, request, principal
    raise BlockchainLegacyFlowDeprecatedError()


@router.get(
    "/transactions/{transaction_id}/status",
    response_model=SuccessEnvelope[SigningStatusData],
    responses=RESPONSES,
)
async def signing_status(
    transaction_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
) -> SuccessEnvelope[SigningStatusData]:
    del transaction_id, request, principal
    raise BlockchainLegacyFlowDeprecatedError()
