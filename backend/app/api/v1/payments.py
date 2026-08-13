from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, status

from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
)
from app.modules.payments.dependencies import PaymentServiceDependency
from app.modules.payments.schemas import (
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
    "/dossiers/{dossier_id}/payment-orders",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def create_payment_order(
    dossier_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.create_order(
        principal,
        dossier_id,
        idempotency_key=idempotency_key,
    )
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(order),
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
    "/webhooks/payments/{provider}",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses={
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
) -> SuccessEnvelope[PaymentOrderData]:
    if provider != service.provider_name:
        from app.modules.payments.errors import PaymentNotFoundError

        raise PaymentNotFoundError("Payment provider was not found.")
    raw_body = await request.body()
    order = await service.process_webhook(
        raw_body=raw_body,
        signature=signature or "",
        timestamp=timestamp or 0,
    )
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
