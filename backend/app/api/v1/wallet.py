from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Request
from pydantic import Field

from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
    SettingsDependency,
)
from app.modules.payments.dependencies import PaymentServiceDependency
from app.modules.payments.schemas import PaymentOrderData, PaymentSchema
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
    result = await service.wallet_service().topup(
        principal.user_id, payload.amount_minor, idempotency_key
    )
    return SuccessEnvelope(
        data=TopupData.model_validate(result),
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
    result = await service.wallet_service().resume(principal.user_id, topup_id)
    return SuccessEnvelope(
        data=TopupData.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
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
