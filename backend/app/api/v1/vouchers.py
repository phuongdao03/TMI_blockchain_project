from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core.errors import DomainError
from app.core.schemas import ResponseMeta, SuccessEnvelope
from app.modules.auth.dependencies import (
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    EmployeeProfileLinkDependency,
    SessionDependency,
)
from app.modules.promotions.models import VoucherCampaign, VoucherClaim
from app.modules.promotions.rate_limit import enforce_promotion_rate_limit
from app.modules.promotions.schemas import (
    PresentationEvent,
    PromotionPolicy,
    RedeemCodeInput,
    VoucherClaimData,
    VoucherOfferData,
)
from app.modules.promotions.service import VoucherService

router = APIRouter(
    prefix="/api/v1/vouchers",
    tags=["vouchers"],
    dependencies=[Depends(enforce_promotion_rate_limit)],
)


def get_voucher_service(session: SessionDependency) -> VoucherService:
    return VoucherService(session)


ServiceDependency = Annotated[VoucherService, Depends(get_voucher_service)]


def _eligible(
    roles: tuple[str, ...], is_employee: bool, permissions: tuple[str, ...] = ()
) -> bool:
    internal = {
        "promotions.manage",
        "promotions.read",
        "users.read",
        "staff.read",
        "review.assign",
        "work.allocations.manage",
        "payments.read",
        "memberships.manage",
        "audit.read",
        "reports.read",
        "public_content.manage",
        "community.manage",
        "community.moderate",
        "dashboard.read",
    }
    return (
        set(roles) == {"USER"}
        and not is_employee
        and not any(code in internal or code.startswith("hr.") for code in permissions)
    )


def _claim_data(row: VoucherClaim) -> VoucherClaimData:
    return VoucherClaimData.model_validate(row).model_copy(
        update={"policy": PromotionPolicy.model_validate(row.policy_json)}
    )


@router.get("/offer", response_model=SuccessEnvelope[VoucherOfferData | None])
async def offer(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ServiceDependency,
    is_employee: EmployeeProfileLinkDependency,
    trigger: Literal["LOGIN", "DASHBOARD"] = "LOGIN",
) -> SuccessEnvelope[VoucherOfferData | None]:
    row = (
        await service.offer(
            principal.user_id, session_id=principal.session_id, trigger=trigger
        )
        if _eligible(principal.roles, is_employee, principal.permissions)
        else None
    )
    data = None
    if row:
        voucher = await service.session.scalar(
            select(VoucherClaim).where(
                VoucherClaim.campaign_id == row.id,
                VoucherClaim.user_id == principal.user_id,
            )
        )
        data = VoucherOfferData.model_validate(row).model_copy(
            update={
                "policy": PromotionPolicy.model_validate(row.policy_json),
                "claimed_voucher_id": voucher.id if voucher else None,
                "expires_at": voucher.expires_at if voucher else None,
            }
        )
    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get("/mine", response_model=SuccessEnvelope[list[VoucherClaimData]])
async def mine(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ServiceDependency,
    is_employee: EmployeeProfileLinkDependency,
) -> SuccessEnvelope[list[VoucherClaimData]]:
    rows = (
        await service.mine(principal.user_id)
        if _eligible(principal.roles, is_employee, principal.permissions)
        else []
    )
    return SuccessEnvelope(
        data=[_claim_data(row) for row in rows],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/{campaign_id}/claim", response_model=SuccessEnvelope[VoucherClaimData])
async def claim(
    campaign_id: UUID,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
    is_employee: EmployeeProfileLinkDependency,
) -> SuccessEnvelope[VoucherClaimData]:
    if not _eligible(principal.roles, is_employee, principal.permissions):
        raise DomainError(
            code="VOUCHER_NOT_ELIGIBLE",
            message=(
                "Voucher chỉ dành cho người dùng thông thường, "
                "không áp dụng cho tài khoản nội bộ."
            ),
            status_code=403,
        )
    row = await service.claim(principal.user_id, campaign_id)
    return SuccessEnvelope(
        data=_claim_data(row),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post("/redeem-code", response_model=SuccessEnvelope[VoucherClaimData])
async def redeem_code(
    payload: RedeemCodeInput,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
    is_employee: EmployeeProfileLinkDependency,
) -> SuccessEnvelope[VoucherClaimData]:
    if not _eligible(principal.roles, is_employee, principal.permissions):
        raise DomainError(
            code="VOUCHER_NOT_ELIGIBLE",
            message="Tài khoản không đủ điều kiện nhận voucher.",
            status_code=403,
        )
    code = payload.code.strip().upper()
    campaign = await service.session.scalar(
        select(VoucherCampaign).where(
            VoucherCampaign.program_type == "CODE",
            VoucherCampaign.active.is_(True),
            VoucherCampaign.public_code == code,
        )
    )
    if campaign is None:
        raise DomainError(
            code="VOUCHER_CODE_INVALID",
            message="Mã ưu đãi không hợp lệ hoặc đã hết hiệu lực.",
            status_code=404,
        )
    row = await service.issue(principal.user_id, campaign.id, reason="public-code")
    return SuccessEnvelope(
        data=_claim_data(row), meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.get("/{voucher_id}", response_model=SuccessEnvelope[VoucherClaimData])
async def voucher_detail(
    voucher_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: ServiceDependency,
    is_employee: EmployeeProfileLinkDependency,
) -> SuccessEnvelope[VoucherClaimData]:
    row = (
        await service.session.scalar(
            select(VoucherClaim).where(
                VoucherClaim.id == voucher_id, VoucherClaim.user_id == principal.user_id
            )
        )
        if _eligible(principal.roles, is_employee, principal.permissions)
        else None
    )
    if row is None:
        raise DomainError(
            code="VOUCHER_NOT_FOUND", message="Không tìm thấy voucher.", status_code=404
        )
    return SuccessEnvelope(
        data=_claim_data(row), meta=ResponseMeta(request_id=request.state.request_id)
    )


@router.post(
    "/{campaign_id}/presentation", response_model=SuccessEnvelope[dict[str, str]]
)
async def presentation_event(
    campaign_id: UUID,
    payload: PresentationEvent,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ServiceDependency,
    is_employee: EmployeeProfileLinkDependency,
) -> SuccessEnvelope[dict[str, str]]:
    if not _eligible(principal.roles, is_employee, principal.permissions):
        raise DomainError(
            code="VOUCHER_NOT_ELIGIBLE",
            message="Ưu đãi không khả dụng.",
            status_code=403,
        )
    await service.presentation_event(
        principal.user_id, campaign_id, principal.session_id, payload.event
    )
    return SuccessEnvelope(
        data={"status": "recorded"},
        meta=ResponseMeta(request_id=request.state.request_id),
    )
