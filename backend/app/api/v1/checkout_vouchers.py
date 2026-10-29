from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.errors import DomainError
from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    SessionDependency,
)
from app.modules.dossiers.models import Dossier
from app.modules.payments.models import PaymentOrder, PaymentStatus
from app.modules.promotions.checkout import PromotionCheckout, utc
from app.modules.promotions.checkout_schemas import (
    AppliedVoucherData,
    ApplyVoucherRequest,
    CheckoutVoucherQuote,
    CheckoutVoucherRequest,
)

router = APIRouter(prefix="/api/v1", tags=["checkout-vouchers"])


async def _owned_order(
    session: SessionDependency, user_id: UUID, identifier: UUID, *, lock: bool = False
) -> PaymentOrder:
    query = (
        select(PaymentOrder)
        .join(Dossier, Dossier.id == PaymentOrder.dossier_id)
        .where(
            PaymentOrder.id == identifier,
            Dossier.owner_user_id == user_id,
        )
    )
    if lock:
        query = query.with_for_update()
    order = await session.scalar(query)
    if order is None:
        raise DomainError(
            code="PAYMENT_NOT_FOUND",
            message="Không tìm thấy khoản thu.",
            status_code=404,
        )
    return order


def order_service(order: PaymentOrder) -> str:
    return (
        "DOSSIER_SUBMISSION"
        if order.metadata_json.get("purpose") == "SUBMISSION_FEE"
        else "DOSSIER_APPROVAL"
    )


@router.post(
    "/checkout-vouchers/quote", response_model=SuccessEnvelope[CheckoutVoucherQuote]
)
async def quote(
    payload: CheckoutVoucherRequest,
    request: Request,
    principal: CurrentPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[CheckoutVoucherQuote]:
    checkout = PromotionCheckout(session)
    product_id: str | None = None
    member_discount = 0
    reference: str | None = None
    if payload.service_code in {"DOSSIER_SUBMISSION", "DOSSIER_APPROVAL"}:
        order = await _owned_order(session, principal.user_id, payload.resource_id)
        if order_service(order) != payload.service_code or order.status not in {
            PaymentStatus.PENDING,
            PaymentStatus.PROCESSING,
        }:
            raise DomainError(
                code="CHECKOUT_INVALID",
                message="Khoản thu không còn chờ thanh toán.",
                status_code=409,
            )
        original = int(
            str(order.metadata_json.get("promotion_original_vnd", order.amount_minor))
        )
        reference = f"payment:{order.id}"
    elif payload.service_code == "MEMBERSHIP":
        from app.modules.memberships.service import MembershipService

        source = await MembershipService(session)._quote(
            principal.user_id,
            payload.resource_id,
            renewal_opt_in=payload.renewal_opt_in,
        )
        original = int(str(source["amount_due_minor"]))
        product_id = str(payload.resource_id)
    else:
        from app.modules.advertising.inventory import AdvertisingInventoryService
        from app.modules.advertising.models import (
            AdvertisingPackage,
            AdvertisingPlacement,
        )

        package = await session.get(AdvertisingPackage, payload.resource_id)
        placement = (
            await session.get(AdvertisingPlacement, package.placement_id)
            if package
            else None
        )
        if (
            package is None
            or placement is None
            or not package.active
            or not placement.enabled
        ):
            raise DomainError(
                code="CHECKOUT_NOT_FOUND",
                message="Gói dịch vụ không khả dụng.",
                status_code=404,
            )
        ad_source = await AdvertisingInventoryService(session)._quote_for_user(
            principal.user_id, placement=placement, package=package, lock_policy=False
        )
        original = int(ad_source["base_amount_vnd"])
        member_discount = int(ad_source["discount_amount_vnd"])
        product_id = str(package.id)
    result = await checkout.quote(
        principal.user_id,
        payload.service_code,
        original,
        product_id=product_id,
        membership_discount_vnd=member_discount,
    )
    if reference is not None:
        active = await checkout.active(reference)
        if active is not None:
            result["selected_voucher_id"] = active.voucher_id
            result["current_payable_vnd"] = active.payable_vnd
    return SuccessEnvelope(
        data=CheckoutVoucherQuote.model_validate(result),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/payment-orders/{order_id}/voucher",
    response_model=SuccessEnvelope[AppliedVoucherData],
)
async def apply(
    order_id: UUID,
    payload: ApplyVoucherRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    session: SessionDependency,
) -> SuccessEnvelope[AppliedVoucherData]:
    async with session.begin():
        order = await _owned_order(session, principal.user_id, order_id, lock=True)
        checkout = PromotionCheckout(session)
        if (
            order.status is not PaymentStatus.PENDING
            or order.provider_order_id is not None
            or utc(order.expires_at) <= checkout.now
        ):
            raise DomainError(
                code="VOUCHER_CHECKOUT_LOCKED",
                message="Chỉ thay đổi voucher trước khi mở cổng thanh toán.",
                status_code=409,
            )
        original = int(
            str(order.metadata_json.get("promotion_original_vnd", order.amount_minor))
        )
        reference = f"payment:{order.id}"
        current = await checkout.active(reference)
        if current is not None and current.voucher_id != payload.voucher_id:
            await checkout.release(reference, reason="Người dùng thay đổi ưu đãi")
        discount = 0
        if payload.voucher_id is not None:
            reservation = await checkout.reserve(
                principal.user_id,
                payload.voucher_id,
                order_reference=reference,
                service_code=order_service(order),
                original_vnd=original,
                expires_at=order.expires_at,
            )
            discount = reservation.discount_vnd
        order.amount_minor = original - discount
        order.metadata_json = {
            **order.metadata_json,
            "promotion_original_vnd": original,
            "promotion_discount_vnd": discount,
            "voucher_id": str(payload.voucher_id) if payload.voucher_id else None,
        }
        await session.flush()
    return SuccessEnvelope(
        data=AppliedVoucherData(
            voucher_id=payload.voucher_id,
            original_vnd=original,
            discount_vnd=discount,
            payable_vnd=original - discount,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
