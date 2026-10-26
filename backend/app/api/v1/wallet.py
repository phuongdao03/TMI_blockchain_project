from datetime import datetime
from io import BytesIO
from typing import Annotated, Literal
from uuid import UUID

import qrcode
from fastapi import APIRouter, Header, Request, Response
from pydantic import Field

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
    SettingsDependency,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.payments.dependencies import PaymentServiceDependency
from app.modules.payments.errors import PaymentForbiddenError, PaymentNotFoundError
from app.modules.payments.schemas import PaymentOrderData, PaymentSchema
from app.modules.payments.service import PaymentService
from app.modules.wallet.models import WalletTopup
from app.modules.wallet.service import read_wallet

router = APIRouter(prefix="/api/v1", tags=["wallet"])


class TopupRequest(PaymentSchema):
    amount_minor: Annotated[int, Field(strict=True, ge=1000, le=1_000_000_000)]


class TopupData(PaymentSchema):
    id: UUID
    order_code: str
    amount_minor: int
    status: str
    checkout_url: str | None
    created_at: datetime
    expires_at: datetime
    paid_at: datetime | None
    qr_payload: str | None = None
    bank_bin: str | None = None
    bank_account_number: str | None = None
    bank_account_name: str | None = None
    transfer_description: str | None = None


def _require_non_admin_wallet(principal: AuthPrincipal) -> None:
    if "SUPER_ADMIN" in principal.roles:
        raise PaymentForbiddenError()


async def _topup_data(service: PaymentService, topup: WalletTopup) -> TopupData:
    result = TopupData.model_validate(topup)
    details = await service.wallet_service().checkout_details(topup.user_id, topup.id)
    if details is None:
        return result
    return result.model_copy(
        update={
            "qr_payload": details.qr_payload,
            "bank_bin": details.bank_bin,
            "bank_account_number": details.bank_account_number,
            "bank_account_name": details.bank_account_name,
            "transfer_description": details.transfer_description,
        }
    )


class JournalData(PaymentSchema):
    id: UUID
    wallet_delta: int
    balance_after: int
    kind: str
    description: str
    created_at: datetime


class WalletData(PaymentSchema):
    balance_minor: int
    currency: Literal["VND"]
    provider: str
    transactions: list[JournalData]
    topups: list[TopupData]


@router.get("/wallet", response_model=SuccessEnvelope[WalletData])
async def get_wallet(
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[WalletData]:
    result = await read_wallet(session, principal.user_id, settings.payment_provider)
    return SuccessEnvelope(
        data=WalletData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/wallet/topups", response_model=SuccessEnvelope[TopupData])
async def create_topup(
    payload: TopupRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> SuccessEnvelope[TopupData]:
    _require_non_admin_wallet(principal)
    result = await service.wallet_service().topup(
        principal.user_id, payload.amount_minor, idempotency_key
    )
    return SuccessEnvelope(
        data=await _topup_data(service, result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/wallet/topups/{topup_id}/reconcile", response_model=SuccessEnvelope[TopupData]
)
async def reconcile_topup(
    topup_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[TopupData]:
    _require_non_admin_wallet(principal)
    result = await service.wallet_service().reconcile(principal.user_id, topup_id)
    return SuccessEnvelope(
        data=TopupData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/wallet/topups/{topup_id}/checkout", response_model=SuccessEnvelope[TopupData]
)
async def resume_topup(
    topup_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
) -> SuccessEnvelope[TopupData]:
    _require_non_admin_wallet(principal)
    result = await service.wallet_service().resume(principal.user_id, topup_id)
    return SuccessEnvelope(
        data=await _topup_data(service, result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/wallet/topups/{topup_id}/qr")
async def get_topup_qr(
    topup_id: UUID,
    principal: CurrentPrincipalDependency,
    service: PaymentServiceDependency,
) -> Response:
    details = await service.wallet_service().checkout_details(
        principal.user_id, topup_id
    )
    if details is None or not details.qr_payload:
        raise PaymentNotFoundError("Payment QR code is unavailable.")
    image = qrcode.make(details.qr_payload)
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


@router.post(
    "/payment-orders/{order_id}/wallet-payment",
    response_model=SuccessEnvelope[PaymentOrderData],
)
async def pay_from_wallet(
    order_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: PaymentServiceDependency,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> SuccessEnvelope[PaymentOrderData]:
    result = await service.pay_with_wallet(
        principal, order_id, idempotency_key=idempotency_key
    )
    return SuccessEnvelope(
        data=PaymentOrderData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
