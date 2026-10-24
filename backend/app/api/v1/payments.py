import csv
from datetime import datetime
from io import BytesIO, StringIO
from typing import Annotated, Any
from uuid import UUID

import qrcode
from fastapi import APIRouter, Header, Query, Request, Response, status

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
from app.modules.payments.dependencies import PaymentServiceDependency
from app.modules.payments.errors import PaymentNotFoundError
from app.modules.payments.models import PaymentStatus
from app.modules.payments.schemas import (
    AdminPaymentHistoryDetailData,
    AdminPaymentHistoryPageData,
    AdminPaymentHistoryRowData,
    AdminPaymentHistorySummaryData,
    AdminPaymentOrderData,
    CancelPaymentOrderRequest,
    FeeObligationData,
    IssuePaymentOrderRequest,
    ManualPaymentConfirmationRequest,
    PaymentCandidateData,
    PaymentOrderData,
    PaymentStatusHistoryData,
    PaymentWaiverData,
    PaymentWaiverRequest,
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


@router.get(
    "/admin/payment-candidates",
    response_model=SuccessEnvelope[list[PaymentCandidateData]],
    responses=PRIVATE_RESPONSES,
)
async def list_payment_candidates(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[list[PaymentCandidateData]]:
    candidates = await service.list_payment_candidates(principal)
    return SuccessEnvelope(
        data=[PaymentCandidateData.model_validate(item) for item in candidates],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/admin/payment-orders",
    response_model=SuccessEnvelope[list[AdminPaymentOrderData]],
    responses=PRIVATE_RESPONSES,
)
async def list_admin_payment_orders(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
    order_status: Annotated[PaymentStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SuccessEnvelope[list[AdminPaymentOrderData]]:
    orders = await service.list_admin_orders(
        principal,
        status=order_status,
        limit=limit,
    )
    return SuccessEnvelope(
        data=[AdminPaymentOrderData.model_validate(item) for item in orders],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


def _history_row_data(row: object) -> AdminPaymentHistoryRowData:
    return AdminPaymentHistoryRowData.model_validate(row)


@router.get(
    "/admin/payment-history",
    response_model=PaginatedSuccessEnvelope[AdminPaymentHistoryPageData],
    responses=PRIVATE_RESPONSES,
)
async def list_admin_payment_history(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
    order_status: Annotated[PaymentStatus | None, Query(alias="status")] = None,
    created_from: Annotated[datetime | None, Query(alias="createdFrom")] = None,
    created_to: Annotated[datetime | None, Query(alias="createdTo")] = None,
    query: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> PaginatedSuccessEnvelope[AdminPaymentHistoryPageData]:
    result, total = await service.list_admin_history(
        principal,
        status=order_status,
        created_from=created_from,
        created_to=created_to,
        query=query,
        page=page,
        page_size=page_size,
    )
    return PaginatedSuccessEnvelope(
        data=AdminPaymentHistoryPageData(
            rows=[_history_row_data(row) for row in result.rows],
            summary=AdminPaymentHistorySummaryData.model_validate(result.summary),
        ),
        meta=ListResponseMeta(
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=total,
        ),
    )


@router.get(
    "/admin/payment-history/export",
    responses={**PRIVATE_RESPONSES, 200: {"content": {"text/csv": {}}}},
)
async def export_admin_payment_history(
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
    order_status: Annotated[PaymentStatus | None, Query(alias="status")] = None,
    created_from: Annotated[datetime | None, Query(alias="createdFrom")] = None,
    created_to: Annotated[datetime | None, Query(alias="createdTo")] = None,
    query: Annotated[str | None, Query(max_length=120)] = None,
) -> Response:
    rows = await service.export_admin_history(
        principal,
        status=order_status,
        created_from=created_from,
        created_to=created_to,
        query=query,
    )
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(
        (
            "Order code",
            "Dossier code",
            "Dossier title",
            "Applicant email",
            "Initiator email",
            "Amount minor",
            "Currency",
            "Status",
            "Created at",
            "Paid at",
            "Description",
        )
    )
    for row in rows:
        order = row.order
        writer.writerow(
            _csv_cell(value)
            for value in (
                order.order_code,
                row.dossier_code,
                row.dossier_title,
                row.applicant_email,
                row.initiated_by_email,
                order.amount_minor,
                order.currency,
                order.status.value,
                order.created_at.isoformat(),
                order.paid_at.isoformat() if order.paid_at else None,
                order.description,
            )
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": 'attachment; filename="payment-history.csv"',
            "X-Content-Type-Options": "nosniff",
        },
    )


def _csv_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@router.get(
    "/admin/payment-history/{order_id}",
    response_model=SuccessEnvelope[AdminPaymentHistoryDetailData],
    responses=PRIVATE_RESPONSES,
)
async def get_admin_payment_history_detail(
    order_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[AdminPaymentHistoryDetailData]:
    detail = await service.get_admin_history_detail(principal, order_id)
    return SuccessEnvelope(
        data=AdminPaymentHistoryDetailData(
            row=_history_row_data(detail.row),
            status_history=[
                PaymentStatusHistoryData.model_validate(item)
                for item in detail.status_history
            ],
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


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


@router.post(
    "/admin/dossiers/{dossier_id}/payment-waiver",
    response_model=SuccessEnvelope[PaymentWaiverData],
    responses=PRIVATE_RESPONSES,
)
async def waive_dossier_payment(
    dossier_id: UUID,
    payload: PaymentWaiverRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ],
) -> SuccessEnvelope[PaymentWaiverData]:
    waiver = await service.waive_payment(
        principal,
        dossier_id,
        idempotency_key=idempotency_key,
        reason=payload.reason,
    )
    return SuccessEnvelope(
        data=PaymentWaiverData.model_validate(waiver),
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
    "/payment-orders/{order_id}/qr",
    responses=PRIVATE_RESPONSES,
)
async def get_payment_order_qr(
    order_id: UUID,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
) -> Response:
    order = await service.get_order(principal, order_id)
    if not order.qr_payload:
        raise PaymentNotFoundError("Payment QR code is unavailable.")
    image = qrcode.make(order.qr_payload)
    output = BytesIO()
    image.save(output)
    return Response(
        content=output.getvalue(),
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
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
    "/payment-orders/{order_id}/checkout-sessions",
    response_model=SuccessEnvelope[PaymentOrderData],
    responses=PRIVATE_RESPONSES,
)
async def start_payment_order_checkout(
    order_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[PaymentOrderData]:
    order = await service.start_order_checkout(principal, order_id)
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
    if order is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
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
