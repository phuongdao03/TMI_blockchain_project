from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.blockchain.human_signing_dependencies import (
    HumanSigningServiceDependency,
)
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

router = APIRouter(prefix="/api/v1/blockchain", tags=["blockchain-signing"])
RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Blockchain signing is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Blockchain resource was not found.", "model": ErrorEnvelope},
    409: {"description": "Blockchain signing conflict.", "model": ErrorEnvelope},
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
    service: HumanSigningServiceDependency,
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
    service: HumanSigningServiceDependency,
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
    service: HumanSigningServiceDependency,
) -> SuccessEnvelope[WalletLinkData | None]:
    view = await service.current_wallet(principal)
    return _success(request, WalletLinkData.model_validate(view) if view else None)  # type: ignore[return-value]


@router.delete(
    "/wallet", response_model=SuccessEnvelope[WalletLinkData], responses=RESPONSES
)
async def revoke_current_wallet(
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: HumanSigningServiceDependency,
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
    service: HumanSigningServiceDependency,
) -> SuccessEnvelope[list[SigningQueueItemData]]:
    views = await service.list_signing_queue(principal)
    return _success(
        request, [SigningQueueItemData.model_validate(view) for view in views]
    )  # type: ignore[return-value]


@router.get(
    "/transactions/{transaction_id}/signing-context",
    response_model=SuccessEnvelope[SigningContextData],
    responses=RESPONSES,
)
async def signing_context(
    transaction_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: HumanSigningServiceDependency,
) -> SuccessEnvelope[SigningContextData]:
    return _success(
        request,
        SigningContextData.model_validate(
            await service.signing_context(principal, transaction_id)
        ),
    )  # type: ignore[return-value]


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
    service: HumanSigningServiceDependency,
) -> SuccessEnvelope[SigningIntentData]:
    view = await service.prepare_intent(
        principal,
        transaction_id=transaction_id,
        connected_wallet=body.connected_wallet,
    )
    return _success(request, SigningIntentData.model_validate(view))  # type: ignore[return-value]


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
    service: HumanSigningServiceDependency,
) -> SuccessEnvelope[SigningStatusData]:
    view = await service.submit_transaction(
        principal,
        transaction_id=transaction_id,
        intent_id=body.intent_id,
        transaction_hash=body.transaction_hash,
        connected_wallet=body.connected_wallet,
    )
    return _success(request, SigningStatusData.model_validate(view))  # type: ignore[return-value]


@router.get(
    "/transactions/{transaction_id}/status",
    response_model=SuccessEnvelope[SigningStatusData],
    responses=RESPONSES,
)
async def signing_status(
    transaction_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: HumanSigningServiceDependency,
) -> SuccessEnvelope[SigningStatusData]:
    return _success(
        request,
        SigningStatusData.model_validate(
            await service.transaction_status(principal, transaction_id)
        ),
    )  # type: ignore[return-value]
