from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response, status

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.payments.dependencies import PaymentServiceDependency
from app.modules.payments.errors import PaymentNotFoundError
from app.modules.payments.schemas import (
    CancelPaymentOrderRequest,
    FeeObligationData,
    IssuePaymentOrderRequest,
    ManualPaymentConfirmationRequest,
    PaymentOrderData,
)

router = APIRouter(prefix="/api/v1", tags=["payments"])

PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required.", "model": ErrorEnvelope},
    403: {"description": "Payment access is forbidden.", "model": ErrorEnvelope},
    404: {"description": "Payment order not found.", "model": ErrorEnvelope},
    409: {"description": "Payment state conflict.", "model": ErrorEnvelope},
    422: {"description": "Payment request is invalid.", "model": ErrorEnvelope},
    503: {"description": "Payment provider unavailable.", "model": ErrorEnvelope},
}


@router.post(
    "/admin/dossiers/{dossier_id}/payment-orders",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def create_payment_order(
    dossier_id: UUID,
    payload: IssuePaymentOrderRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.issue_order(
        principal,
        dossier_id,
        idempotency_key=idempotency_key,
        amount_minor=payload.amount_minor,
        currency=payload.currency,
        description=payload.description,
        due_at=payload.due_at,
    )
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/dossiers/{dossier_id}/fee-obligation",
    response_model=SuccessEnvelope[FeeObligationData],
    responses=PRIVATE_RESPONSES,
)
async def get_dossier_fee_obligation(
    dossier_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[FeeObligationData]:
    obligation = await service.get_fee_obligation_for_dossier(principal, dossier_id)
    return SuccessEnvelope(
        data=FeeObligationData.model_validate(obligation),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/dossiers/{dossier_id}/active-payment-order",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def get_active_payment_order(
    dossier_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.get_active_order_for_dossier(principal, dossier_id)
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/billing/obligations/{obligation_id}/checkout-sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def create_obligation_checkout_session(
    obligation_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.create_checkout_for_obligation(
        principal,
        obligation_id,
        idempotency_key=idempotency_key,
    )
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/payment-orders/by-provider-reference",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def get_payment_order_by_provider_reference(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
    provider_order_id: Annotated[
        str,
        Query(alias="providerOrderId", min_length=1, max_length=128),
    ],
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.get_order_by_provider_reference(
        principal,
        provider_order_id,
    )
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/payment-orders/{order_id}",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def get_payment_order(
    order_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.get_order(principal, order_id)
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/payment-orders/{order_id}/cancel",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def cancel_payment_order(
    order_id: UUID,
    payload: CancelPaymentOrderRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.cancel_order(
        principal,
        order_id,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/webhooks/payments/{provider}",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses={
        204: {"description": "Verified PayOS registration probe acknowledged."},
        404: PRIVATE_RESPONSES[404],
        409: PRIVATE_RESPONSES[409],
        422: PRIVATE_RESPONSES[422],
    },
)
async def process_payment_webhook(
    provider: str,
    request: Request,
    service: PaymentServiceDependency,
    signature: Annotated[
        str | None,
        Header(alias="X-Payment-Signature", min_length=64, max_length=128),
    ] = None,
    timestamp: Annotated[
        int | None,
        Header(alias="X-Payment-Timestamp", ge=0),
    ] = None,
) -> SuccessEnvelope[PaymentOrderData] | Response:
    if provider != service.provider_name:
        raise PaymentNotFoundError("Payment provider was not found.")
    raw_body = await request.body()
    try:
        order = await service.process_webhook(
            raw_body=raw_body,
            signature=signature or "",
            timestamp=timestamp or 0,
        )
    except PaymentNotFoundError:
        # PayOS sends a correctly signed sample transaction while confirming a
        # webhook URL. The signature has already been verified by the gateway;
        # acknowledge that probe without creating or changing payment data.
        if provider == "payos":
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        raise
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/payment-orders/{order_id}/confirm-manual",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def confirm_payment_manually(
    order_id: UUID,
    payload: ManualPaymentConfirmationRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.confirm_manual(
        principal,
        order_id,
        evidence_reference=payload.evidence_reference,
        note=payload.note,
    )
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/admin/payment-orders/{order_id}/reconcile",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def reconcile_payment_order(
    order_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.reconcile_order(principal, order_id)
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
